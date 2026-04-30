import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const files = {
  packageJson: path.join(projectRoot, "package.json"),
  postcssConfig: path.join(projectRoot, "postcss.config.mjs"),
  globalCss: path.join(projectRoot, "src/app/globals.css"),
  smartAllCss: path.join(
    projectRoot,
    "src/components/smartall/SmartAllHome.module.css",
  ),
};

const packageJson = JSON.parse(readFileSync(files.packageJson, "utf8"));
const postcssConfig = readFileSync(files.postcssConfig, "utf8");
const globalCss = readFileSync(files.globalCss, "utf8");
const smartAllCss = readFileSync(files.smartAllCss, "utf8");

const errors = [];

if (!packageJson.scripts?.dev?.includes("--webpack")) {
  errors.push("package.json scripts.dev must keep --webpack for local Next dev.");
}

if (postcssConfig.includes("@tailwindcss/postcss")) {
  errors.push("postcss.config.mjs must not enable @tailwindcss/postcss.");
}

if (/@import\s+["']tailwindcss["']/.test(globalCss)) {
  errors.push('globals.css must not import "tailwindcss".');
}

if (/^:global\(\.interaction-zone/m.test(smartAllCss)) {
  errors.push(
    "SmartAllHome.module.css interaction-zone globals must stay scoped under .smartallStage.",
  );
}

if (errors.length > 0) {
  console.error("Frontend dev config check failed:");

  for (const error of errors) {
    console.error(`- ${error}`);
  }

  process.exit(1);
}
