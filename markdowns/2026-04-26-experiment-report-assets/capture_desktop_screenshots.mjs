import fs from "node:fs/promises";
import path from "node:path";

const outDir = "/Users/li/PycharmProjects/CloudClass/markdowns/2026-04-26-experiment-report-assets/desktop_screenshots";
await fs.mkdir(outDir, { recursive: true });

async function connectCdp() {
  const targets = await (await fetch("http://127.0.0.1:9223/json")).json();
  const page = targets.find((target) => target.type === "page") || targets[0];
  if (!page?.webSocketDebuggerUrl) {
    throw new Error("No Chrome page target found on 127.0.0.1:9223");
  }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  let id = 0;
  const pending = new Map();
  const listeners = new Map();

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(JSON.stringify(message.error)));
      } else {
        resolve(message.result);
      }
      return;
    }
    if (message.method && listeners.has(message.method)) {
      for (const listener of listeners.get(message.method)) {
        listener(message.params);
      }
    }
  };

  function send(method, params = {}) {
    const callId = ++id;
    ws.send(JSON.stringify({ id: callId, method, params }));
    return new Promise((resolve, reject) => pending.set(callId, { resolve, reject }));
  }

  function once(method) {
    return new Promise((resolve) => {
      if (!listeners.has(method)) {
        listeners.set(method, new Set());
      }
      const listener = (params) => {
        listeners.get(method).delete(listener);
        resolve(params);
      };
      listeners.get(method).add(listener);
    });
  }

  return { send, once, close: () => ws.close() };
}

const cdp = await connectCdp();
await cdp.send("Page.enable");
await cdp.send("Runtime.enable");
await cdp.send("Network.enable");
await cdp.send("Emulation.setDeviceMetricsOverride", {
  width: 1365,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
});

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function navigate(url) {
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url });
  await loaded;
  await delay(700);
}

async function login(username, password) {
  await navigate("http://127.0.0.1:8000/accounts/login/");
  await cdp.send("Runtime.evaluate", {
    expression:
      `document.querySelector('#id_username').value = ${JSON.stringify(username)};` +
      `document.querySelector('#id_password').value = ${JSON.stringify(password)};` +
      "document.querySelector('form').submit();",
  });
  await cdp.once("Page.loadEventFired");
  await delay(700);
}

async function screenshot(name) {
  const metrics = await cdp.send("Page.getLayoutMetrics");
  const width = Math.max(Math.ceil(metrics.contentSize.width || 1365), 1365);
  const height = Math.max(Math.ceil(metrics.contentSize.height || 900), 900);
  const result = await cdp.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width, height, scale: 1 },
  });
  await fs.writeFile(path.join(outDir, name), Buffer.from(result.data, "base64"));
}

async function gotoAndShot(url, name) {
  await navigate(url);
  await screenshot(name);
}

async function logout() {
  await navigate("http://127.0.0.1:8000/accounts/logout/");
}

await gotoAndShot("http://127.0.0.1:8000/", "00-home-首页-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/accounts/login/", "01-login-登录界面-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/accounts/register/", "02-register-学生注册界面-桌面.png");

await login("admin", "admin123456");
await gotoAndShot("http://127.0.0.1:8000/dashboard/admin/", "10-admin-dashboard-管理员工作台-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/announcements/create/", "11-admin-announcement-create-公告管理-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/banners/create/", "12-admin-banner-create-Banner管理-桌面.png");
await logout();

await login("teacher01", "teacher123456");
await gotoAndShot("http://127.0.0.1:8000/dashboard/teacher/", "20-teacher-dashboard-教师工作台-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/courses/teacher/manage/", "21-teacher-course-manage-课程管理-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/courses/teacher/1/analytics/", "22-teacher-course-analytics-课程统计-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/ai/", "23-teacher-ai-center-AI助教中心-桌面.png");
await logout();

await login("student01", "student123456");
await gotoAndShot("http://127.0.0.1:8000/dashboard/student/", "30-student-dashboard-学生工作台-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/courses/", "31-student-course-list-课程中心-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/courses/1/", "32-student-course-detail-课程详情与选课-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/courses/recommendations/", "33-student-recommendations-个性化推荐-桌面.png");
await gotoAndShot("http://127.0.0.1:8000/ai/student-chat/", "34-student-ai-chat-AI聊天-桌面.png");

cdp.close();
const files = (await fs.readdir(outDir)).sort();
console.log(`Generated ${files.length} desktop screenshots in ${outDir}`);
