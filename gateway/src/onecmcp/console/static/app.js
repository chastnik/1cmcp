const main = document.getElementById("main");
const sidebar = document.getElementById("sidebar");
const tokenKey = "onecmcp-console-token";

function token() {
  return localStorage.getItem(tokenKey) || "";
}

function setToken(value) {
  if (value) localStorage.setItem(tokenKey, value);
  else localStorage.removeItem(tokenKey);
}

function authHeaders() {
  const value = token();
  return value ? { Authorization: "Bearer " + value } : {};
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  if (!response.ok) {
    const error = new Error((data && (data.detail || data.title)) || response.statusText);
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

function helpBtn(text) {
  const safe = String(text || "").replace(/"/g, "&quot;");
  return `<button type="button" class="help-tip" data-help="${safe}" aria-label="Подсказка: ${safe}">?</button>`;
}

function fieldValue(form, name) {
  const el = form.elements.namedItem(name);
  return el && "value" in el ? String(el.value).trim() : "";
}

function route() {
  const hash = (location.hash || "#/").slice(1);
  return hash.startsWith("/") ? hash : "/" + hash;
}

function navLink(href, label, current) {
  const active = current === href || (href !== "#/" && current.startsWith(href.slice(1))) ? " active" : "";
  return `<a class="${active.trim()}" href="${href}">${label}</a>`;
}

async function render() {
  const path = route();
  let docs = { pages: [] };
  try { docs = await api("/console/api/docs"); } catch { docs = { pages: [] }; }
  const groups = {};
  for (const page of docs.pages || []) {
    (groups[page.group] ||= []).push(page);
  }
  let nav = `<a href="#/">Обзор</a>${navLink("#/api", "HTTP API", path)}${navLink("#/mcp", "Инструменты MCP", path)}${navLink("#/admin", "Администрирование", path)}`;
  for (const [group, pages] of Object.entries(groups)) {
    nav += `<h2>${group}</h2>`;
    for (const page of pages) {
      nav += navLink("#/docs/" + page.id, page.title, path);
    }
  }
  sidebar.innerHTML = nav;
  try {
    if (path === "/" || path === "") await renderHome();
    else if (path.startsWith("/docs/")) await renderDoc(path.slice(6));
    else if (path === "/api") await renderApi();
    else if (path === "/mcp") await renderMcp();
    else if (path.startsWith("/admin")) await renderAdmin();
    else main.innerHTML = "<div class='card'><h1>Нет такой страницы</h1></div>";
  } catch (err) {
    main.innerHTML = `<div class="card"><h1>Ошибка</h1><p class="flash err">${err.message}</p></div>`;
  }
}

async function renderHome() {
  const catalog = await api("/console/api/catalog");
  main.innerHTML = `
    <h1>Консоль 1cmcp</h1>
    <p class="muted">Версия ${catalog.version}. Здесь же справочник методов и инструкции внедренца. Базы и операторы — во вкладке «Администрирование».</p>
    <div class="card">
      <p>REST-методов: <strong>${catalog.rest.length}</strong>. MCP-инструментов: <strong>${catalog.mcp.length}</strong>.</p>
      <p>Агенты ходят в <code>/mcp</code> или <code>/v1</code>. Эта консоль — для человека: прочитать контракт, настроить шлюз, завести оператора.</p>
    </div>`;
}

async function renderDoc(id) {
  const page = await api("/console/api/docs/" + id + ".md");
  main.innerHTML = `<h1>${page.title}</h1><article class="doc-body card">${page.html}</article>`;
  main.querySelectorAll("a[href$='.md']").forEach((link) => {
    const href = link.getAttribute("href") || "";
    const slug = href.replace(/^\.\.\//, "").replace(/\.md$/, "");
    link.setAttribute("href", "#/docs/" + slug);
  });
}

async function renderApi() {
  const catalog = await api("/console/api/catalog");
  const rows = catalog.rest.map((item) => `
    <tr>
      <td><span class="method">${item.method}</span></td>
      <td><code>${item.path}</code></td>
      <td>${item.summary || ""}</td>
    </tr>
    ${item.description ? `<tr><td></td><td colspan="2" class="muted">${item.description.replace(/\n/g, "<br>")}</td></tr>` : ""}
  `).join("");
  main.innerHTML = `<h1>HTTP API</h1><p class="muted">Контракт слоя A и REST-проекция шлюза. Живая спецификация: <a href="/openapi.yaml">/openapi.yaml</a>.</p><div class="card"><table><thead><tr><th>Метод</th><th>Путь</th><th>Смысл</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function renderMcp() {
  const catalog = await api("/console/api/catalog");
  const rows = catalog.mcp.map((item) => `<tr><td><code>${item.name}</code></td><td>${item.description || ""}</td></tr>`).join("");
  main.innerHTML = `<h1>Инструменты MCP</h1><p class="muted">Имена совпадают по смыслу с HTTP. Подключение: stdio <code>python -m onecmcp mcp</code> или streamable HTTP <code>/mcp</code>.</p><div class="card"><table><thead><tr><th>Инструмент</th><th>Зачем</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function renderAdmin() {
  if (!token()) {
    main.innerHTML = `
      <h1>Администрирование</h1>
      <p class="muted">Первый вход — токеном <code>ADMIN_BOOTSTRAP_TOKEN</code>. Дальше заведите оператора и входите логином.</p>
      <form class="card" id="login-form">
        <label class="field"><span>Токен первого входа ${helpBtn("Секрет из .env на старте шлюза. После заведения оператора нужен только как аварийный ключ.")}</span><input id="login-token" name="token" type="text" autocomplete="off" spellcheck="false" placeholder="ADMIN_BOOTSTRAP_TOKEN"></label>
        <p class="muted">или логин оператора</p>
        <label class="field"><span>Логин оператора ${helpBtn("Пользователь этой консоли, не пользователь 1С. Клиенты интеграции по-прежнему выпускаются обработкой в 1С.")}</span><input id="login-name" name="login" autocomplete="username"></label>
        <label class="field"><span>Пароль ${helpBtn("Пароль оператора консоли, минимум 8 символов при создании.")}</span><input id="login-password" name="password" type="password" autocomplete="current-password"></label>
        <button type="submit">Войти</button>
        <p class="flash err" id="login-error" hidden></p>
      </form>`;
    document.getElementById("login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.target;
      try {
        const body = {};
        const tokenValue = fieldValue(form, "token");
        const loginValue = fieldValue(form, "login");
        const passwordValue = form.elements.namedItem("password")?.value || "";
        if (tokenValue) body.token = tokenValue;
        if (loginValue) body.login = loginValue;
        if (passwordValue) body.password = passwordValue;
        if (!body.token && !body.login) {
          throw new Error("Введите токен первого входа или логин оператора");
        }
        const session = await api("/console/api/login", { method: "POST", body: JSON.stringify(body) });
        setToken(session.access_token);
        render();
      } catch (err) {
        const box = document.getElementById("login-error");
        box.hidden = false;
        box.textContent = err.message;
      }
    });
    return;
  }
  let settings;
  try {
    settings = await api("/console/api/settings");
  } catch (err) {
    if (err.status === 401) {
      setToken("");
      return renderAdmin();
    }
    throw err;
  }
  const bases = await api("/console/api/bases");
  const operators = await api("/console/api/operators");
  const numeric = new Set(["gateway_port", "onec_timeout_seconds", "meta_cache_ttl_seconds", "rate_limit_per_minute"]);
  const fields = settings.fields.map((field) => {
    const value = settings.values[field.name];
    const readonly = field.source === "env";
    let placeholder = "";
    if (field.secret && field.source === "env") {
      placeholder = settings.values.admin_bootstrap_token_set ? "задан в env" : "не задан";
    } else if (field.secret) {
      placeholder = settings.values.onec_token_set ? "сохранён, пустое — не менять" : "";
    }
    const display = field.secret ? "" : (value ?? "");
    const kind = numeric.has(field.name) ? "number" : "text";
    return `<label class="field"><span>${field.label} ${helpBtn(field.help)}</span><input name="${field.name}" type="${kind}" ${readonly ? "readonly" : ""} value="${String(display ?? "").replace(/"/g, "&quot;")}" placeholder="${placeholder.replace(/"/g, "&quot;")}"></label>`;
  }).join("");
  const baseRows = (bases.items || []).map((item, index) => `
    <div class="card" data-base="${index}">
      <label class="field"><span>id базы ${helpBtn("Короткий идентификатор для X-Tenant и пути /t/{id}/v1/…")}</span><input name="id" value="${item.id || ""}"></label>
      <label class="field"><span>URL слоя A ${helpBtn("Корень HTTP-сервиса без /v1. Живая 1С: http(s)://{host}/{ib}/hs/mcp")}</span><input name="url" value="${item.url || ""}"></label>
      <label class="field"><span>Токен клиента ${helpBtn("Plaintext из обработки «Администрирование коннектора» в 1С. Не хеш SHA-256.")}</span><input name="token" type="password" placeholder="${item.token_set ? "сохранён, пустое — не менять" : ""}"></label>
    </div>`).join("");
  const people = (operators.items || []).map((item) => `<li><code>${item.login}</code></li>`).join("") || "<li class='muted'>Пока никого — заведите первого оператора.</li>";
  main.innerHTML = `
    <h1>Администрирование</h1>
    <p class="muted">Env нужен только чтобы поднять процесс. Базы, токены подключений и операторы консоли живут здесь.</p>
    <div id="admin-flash"></div>
    <form class="card" id="settings-form">
      <h2>Настройки шлюза</h2>
      ${fields}
      <button type="submit">Сохранить настройки</button>
    </form>
    <form class="card" id="bases-form">
      <h2>Базы 1С</h2>
      <p class="muted">Подключение информационных баз. Клиентов агентов (лимиты, ACL) по-прежнему заводите в 1С.</p>
      <div id="bases-list">${baseRows || ""}</div>
      <button type="button" class="secondary" id="add-base">Добавить базу</button>
      <button type="submit">Сохранить базы</button>
    </form>
    <form class="card" id="ops-form">
      <h2>Операторы консоли</h2>
      <ul>${people}</ul>
      <label class="field"><span>Новый логин ${helpBtn("Учётка входа в эту веб-консоль, не пользователь информационной базы 1С.")}</span><input id="new-operator-login" name="login" required minlength="2" autocomplete="off"></label>
      <label class="field"><span>Пароль ${helpBtn("Минимум 8 символов. Хранится как PBKDF2-хеш в console.json.")}</span><input id="new-operator-password" name="password" type="password" required minlength="8" autocomplete="new-password"></label>
      <button type="submit">Завести оператора</button>
    </form>
    <p><button type="button" class="secondary" id="logout">Выйти</button></p>`;
  document.getElementById("logout").onclick = () => { setToken(""); render(); };
  document.getElementById("add-base").onclick = () => {
    const list = document.getElementById("bases-list");
    list.insertAdjacentHTML("beforeend", `<div class="card"><label class="field"><span>id базы ${helpBtn("Короткий идентификатор тенанта.")}</span><input name="id"></label><label class="field"><span>URL слоя A ${helpBtn("Корень HTTP-сервиса без /v1.")}</span><input name="url"></label><label class="field"><span>Токен клиента ${helpBtn("Plaintext токена клиента интеграции.")}</span><input name="token" type="password"></label></div>`);
  };
  document.getElementById("settings-form").onsubmit = async (event) => {
    event.preventDefault();
    const body = {};
    for (const field of settings.fields) {
      if (field.source !== "ui") continue;
      const input = event.target.elements[field.name];
      if (!input) continue;
      if (field.secret && !input.value) continue;
      body[field.name] = input.type === "number" ? Number(input.value) : input.value;
    }
    try {
      await api("/console/api/settings", { method: "PUT", body: JSON.stringify(body) });
      flash("Настройки сохранены", true);
    } catch (err) { flash(err.message, false); }
  };
  document.getElementById("bases-form").onsubmit = async (event) => {
    event.preventDefault();
    const items = [...event.target.querySelectorAll("#bases-list .card")].map((card) => ({
      id: card.querySelector("[name=id]").value.trim(),
      url: card.querySelector("[name=url]").value.trim(),
      token: card.querySelector("[name=token]").value,
    })).filter((item) => item.id && item.url);
    try {
      await api("/console/api/bases", { method: "PUT", body: JSON.stringify({ items, default_id: items[0] && items[0].id }) });
      flash("Базы сохранены", true);
      render();
    } catch (err) { flash(err.message, false); }
  };
  document.getElementById("ops-form").onsubmit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/console/api/operators", { method: "POST", body: JSON.stringify({ login: form.get("login"), password: form.get("password") }) });
      flash("Оператор создан", true);
      render();
    } catch (err) { flash(err.message, false); }
  };
}

function flash(text, ok) {
  const box = document.getElementById("admin-flash");
  if (!box) return;
  box.innerHTML = `<p class="flash ${ok ? "ok" : "err"}">${text}</p>`;
}

window.addEventListener("hashchange", render);
render();
