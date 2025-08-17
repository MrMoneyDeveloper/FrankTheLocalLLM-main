use include_dir::{include_dir, Dir};

const DIST: Dir = include_dir!("../app/dist");

fn main() {
    println!("cargo:rerun-if-changed=../app/dist");
    let out_dir = std::env::var("OUT_DIR").unwrap();
    DIST.extract(std::path::Path::new(&out_dir).join("dist")).unwrap();
}
