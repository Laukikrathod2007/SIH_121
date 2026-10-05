import { cpSync, mkdirSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = resolve(projectRoot, 'node_modules/cesium/Build/Cesium');
const targetRoot = resolve(projectRoot, 'public/cesiumStatic');
const requiredDirectories = ['Workers', 'ThirdParty', 'Assets', 'Widgets'];

mkdirSync(targetRoot, { recursive: true });
for (const directory of requiredDirectories) {
  const source = resolve(sourceRoot, directory);
  const target = resolve(targetRoot, directory);
  const sourceRelative = relative(sourceRoot, source);
  const targetRelative = relative(targetRoot, target);
  if (!sourceRelative || !targetRelative || isAbsolute(sourceRelative) || isAbsolute(targetRelative)
    || sourceRelative.startsWith('..') || targetRelative.startsWith('..')) {
    throw new Error('Cesium static asset path escaped its project directory.');
  }
  cpSync(source, target, { recursive: true, force: true });
}

console.log(`Prepared Cesium static assets in ${targetRoot}`);
