#!/usr/bin/env node
import { spawn } from "node:child_process";

const child = spawn("npx", ["-y", "timeweb-mcp-server@0.1.3"], {
  stdio: ["pipe", "pipe", "pipe"],
  env: process.env,
});

let stdoutBuffer = "";

const flushStdoutLines = (flushRemainder = false) => {
  while (true) {
    const newlineIndex = stdoutBuffer.indexOf("\n");
    if (newlineIndex === -1) {
      break;
    }

    const line = stdoutBuffer.slice(0, newlineIndex + 1);
    stdoutBuffer = stdoutBuffer.slice(newlineIndex + 1);

    const trimmed = line.trim();
    if (trimmed.length === 0 || trimmed === "Timeweb MCP server started") {
      continue;
    }

    if (trimmed.startsWith("{")) {
      process.stdout.write(line);
      continue;
    }

    process.stderr.write(`[timeweb-mcp stdout] ${trimmed}\n`);
  }

  if (flushRemainder && stdoutBuffer.length > 0) {
    const trimmed = stdoutBuffer.trim();
    if (trimmed.length > 0 && trimmed !== "Timeweb MCP server started") {
      if (trimmed.startsWith("{")) {
        process.stdout.write(`${stdoutBuffer}\n`);
      } else {
        process.stderr.write(`[timeweb-mcp stdout] ${trimmed}\n`);
      }
    }
    stdoutBuffer = "";
  }
};

process.stdin.on("data", (chunk) => {
  child.stdin.write(chunk);
});

process.stdin.on("end", () => {
  child.stdin.end();
});

child.stdout.on("data", (chunk) => {
  stdoutBuffer += chunk.toString("utf8");
  flushStdoutLines();
});

child.stderr.on("data", (chunk) => {
  process.stderr.write(chunk);
});

child.stdout.on("end", () => {
  flushStdoutLines(true);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});

child.on("error", (error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(1);
});
