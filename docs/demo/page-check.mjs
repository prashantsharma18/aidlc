// Demo page check: drives headless Chrome over the DevTools protocol (Node 22's built-in WebSocket,
// no dependency), tracks one shipment on the portal and prints what a customer sees.
//   node docs/demo/page-check.mjs <portal url> <shipment id> [screenshot.png]
// Prints JSON: {"id", "text", "window"}; "window" is the "Estimated delivery: ..." line or null.
// Runs in Europe/London with locale en-GB, so the output is the same on any machine.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, id, shot] = process.argv.slice(2);
if (!url || !id) {
  console.error("usage: node page-check.mjs <portal url> <shipment id> [screenshot.png]");
  process.exit(2);
}
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "page-check-"));
const chrome = spawn("google-chrome", ["--headless=new", `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, "--no-first-run", "--window-size=900,700", "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pageSocket() {
  for (let i = 0; i < 50; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = targets.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* Chrome is still starting */ }
    await sleep(100);
  }
  throw new Error("Chrome did not start");
}

function client(ws) {
  let next = 0;
  const pending = new Map();
  const waiters = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id !== undefined && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    } else if (msg.method) {
      for (const w of waiters.filter((w) => w.method === msg.method)) {
        waiters.splice(waiters.indexOf(w), 1);
        w.resolve(msg.params);
      }
    }
  });
  return {
    send: (method, params = {}) => new Promise((resolve, reject) => {
      const n = ++next;
      pending.set(n, { resolve, reject });
      ws.send(JSON.stringify({ id: n, method, params }));
    }),
    once: (method) => new Promise((resolve) => waiters.push({ method, resolve })),
  };
}

const TRACK = (shipment) => `(async () => {
  const input = document.querySelector("#shipment-id");
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  setValue.call(input, ${JSON.stringify(shipment)});
  input.dispatchEvent(new Event("input", { bubbles: true }));
  document.querySelector("button[type=submit]").click();
  for (let i = 0; i < 50 && !document.querySelector("dl, [role=alert]"); i++) await new Promise((r) => setTimeout(r, 100));
  await new Promise((r) => setTimeout(r, 500));   // the flags load and the window line render
  return document.querySelector("main").innerText;
})()`;

let exit = 0;
try {
  const ws = new WebSocket(await pageSocket());
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  const cdp = client(ws);
  await cdp.send("Page.enable");
  await cdp.send("Emulation.setTimezoneOverride", { timezoneId: "Europe/London" });
  await cdp.send("Emulation.setLocaleOverride", { locale: "en-GB" });
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url });
  await loaded;
  await sleep(500);
  const { result } = await cdp.send("Runtime.evaluate", { expression: TRACK(id), awaitPromise: true, returnByValue: true });
  const text = String(result.value ?? "");
  const line = text.split("\n").find((l) => l.startsWith("Estimated delivery:")) ?? null;
  if (shot) {
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(shot, Buffer.from(data, "base64"));
  }
  console.log(JSON.stringify({ id, text, window: line }));
  ws.close();
} catch (error) {
  console.error(`page-check: ${error.message}`);
  exit = 1;
} finally {
  chrome.kill();
  await sleep(200);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(exit);
