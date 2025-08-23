const esbuild = require('esbuild');
const vuePlugin = require('esbuild-plugin-vue3');
const tailwindPlugin = require('esbuild-plugin-tailwindcss').default;
const fs = require('fs');

const serve = process.argv.includes('--serve');
const port = Number(process.env.PORT) || 5173;

const buildOptions = {
  entryPoints: ['app.js'],
  bundle: true,
  sourcemap: true,
  outfile: 'dist/bundle.js',
  plugins: [vuePlugin(), tailwindPlugin()],
  define: {
    __VUE_OPTIONS_API__: 'true',
    __VUE_PROD_DEVTOOLS__: 'false'
  },
  format: 'esm'
};

if (serve) {
  esbuild.context(buildOptions).then(ctx => {
    ctx.watch();
    return ctx.serve({ servedir: '.', port });
  }).catch(() => process.exit(1));
} else {
  esbuild.build({ ...buildOptions, minify: true }).then(() => {
    fs.mkdirSync('dist', { recursive: true });
    fs.copyFileSync('sw.js', 'dist/sw.js');
    const html = fs.readFileSync('index.html', 'utf8').replace('dist/bundle.js', 'bundle.js');
    fs.writeFileSync('dist/index.html', html);
  }).catch(() => process.exit(1));
}
