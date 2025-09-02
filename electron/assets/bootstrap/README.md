Local Bootstrap assets

This folder is reserved for local Bootstrap assets if you prefer copying files out of `node_modules/bootstrap/dist` for offline packaging.

Example (manual copy):
- Copy `node_modules/bootstrap/dist/css/bootstrap.min.css` to `electron/assets/bootstrap/bootstrap.min.css`
- Copy `node_modules/bootstrap/dist/js/bootstrap.bundle.min.js` to `electron/assets/bootstrap/bootstrap.bundle.min.js`

The renderer currently references Bootstrap directly from `node_modules` for development. Update paths to use this folder if you decide to vendor the files.

