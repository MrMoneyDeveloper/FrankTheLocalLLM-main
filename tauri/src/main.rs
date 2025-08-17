use std::{fs, io::{BufRead, BufReader}, path::PathBuf, process::{Command, Stdio}, sync::Mutex};

use clap::Parser;
use dirs::home_dir;
use serde::{Deserialize, Serialize};
use tauri::{Manager, State};

#[derive(Parser)]
struct Cli {
    /// Force launching in the system browser
    #[arg(long)]
    browser: bool,
}

#[derive(Serialize, Deserialize, Copy, Clone, PartialEq, Eq)]
enum Mode {
    Desktop,
    Browser,
}

#[derive(Serialize, Deserialize)]
struct Config {
    mode: Mode,
}

impl Default for Config {
    fn default() -> Self {
        Self { mode: Mode::Desktop }
    }
}

fn config_path() -> PathBuf {
    home_dir()
        .expect("home dir")
        .join(".smartpad")
        .join("config.json")
}

fn load_config() -> Config {
    let path = config_path();
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_config(cfg: &Config) -> std::io::Result<()> {
    let path = config_path();
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir)?;
    }
    fs::write(path, serde_json::to_string(cfg).unwrap())
}

struct BackendPort(Mutex<u16>);
struct ModeState(Mutex<Mode>);

#[tauri::command]
fn toggle_mode(state: State<'_, ModeState>) -> Result<String, String> {
    let mut mode = state.0.lock().unwrap();
    *mode = match *mode {
        Mode::Desktop => Mode::Browser,
        Mode::Browser => Mode::Desktop,
    };
    let cfg = Config { mode: *mode };
    save_config(&cfg).map_err(|e| e.to_string())?;
    Ok(match *mode {
        Mode::Desktop => "desktop",
        Mode::Browser => "browser",
    }
    .to_string())
}

fn main() {
    let cli = Cli::parse();

    let mut child = Command::new("python")
        .arg("../backend/main.py")
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to spawn backend");

    let stdout = child.stdout.take().expect("no stdout");
    let mut reader = BufReader::new(stdout);
    let mut line = String::new();
    reader.read_line(&mut line).expect("read line");
    let port: u16 = line.trim().parse().expect("parse port");

    let mut cfg = load_config();
    let browser_mode = if cli.browser {
        cfg.mode = Mode::Browser;
        let _ = save_config(&cfg);
        true
    } else {
        cfg.mode == Mode::Browser
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            let port = *app.state::<BackendPort>().0.lock().unwrap();
            let mode = *app.state::<ModeState>().0.lock().unwrap();
            if mode == Mode::Browser {
                let url = format!("http://127.0.0.1:{port}");
                let _ = tauri::api::shell::open(&app.shell_scope(), url, None);
            } else if let Some(win) = app.get_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![toggle_mode])
        .setup(move |app| {
            if browser_mode {
                let url = format!("http://127.0.0.1:{port}");
                tauri::api::shell::open(&app.shell_scope(), url, None)?;
            } else {
                tauri::WindowBuilder::new(app, "main", tauri::WindowUrl::App("index.html".into()))
                    .build()?;
            }
            Ok(())
        })
        .manage(BackendPort(Mutex::new(port)))
        .manage(ModeState(Mutex::new(cfg.mode)))
        .run(tauri::generate_context!())
        .expect("error running tauri app");
}
