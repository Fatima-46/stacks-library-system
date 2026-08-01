/* Stacks — frontend logic. Vanilla JS, talks to the Flask REST API. */

const API = "/api";

// ---------------- Tabs ----------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");

    if (tab.dataset.tab === "dashboard") loadStats();
    if (tab.dataset.tab === "books") loadBooks();
    if (tab.dataset.tab === "members") loadMembers();
    if (tab.dataset.tab === "history") loadHistory();
  });
});

// ---------------- Toast ----------------
function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "toast" + (isError ? " error" : "");
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.hidden = true), 3500);
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

// ---------------- Dashboard ----------------
async function loadStats() {
  try {
    const s = await api("/stats");
    document.getElementById("stat-books").textContent = s.total_books;
    document.getElementById("stat-available").textContent = s.available_books;
    document.getElementById("stat-members").textContent = s.total_members;
    document.getElementById("stat-loans").textContent = s.active_loans;
    document.getElementById("stat-fines").textContent = `$${s.total_unpaid_fines.toFixed(2)}`;
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------- Books ----------------
async function loadBooks(query = "") {
  const tbody = document.getElementById("books-table-body");
  tbody.innerHTML = `<tr><td colspan="6">Loading&hellip;</td></tr>`;
  try {
    const books = await api(query ? `/books/search?q=${encodeURIComponent(query)}` : "/books");
    if (!books.length) {
      tbody.innerHTML = `<tr><td colspan="6">No books found.</td></tr>`;
      return;
    }
    tbody.innerHTML = books
      .map(
        (b) => `
      <tr>
        <td>${escapeHtml(b.id)}</td>
        <td>${escapeHtml(b.title)}</td>
        <td>${escapeHtml(b.author)}</td>
        <td>${escapeHtml(b.genre)}</td>
        <td class="${b.available_copies === 0 ? "qty-empty" : ""}">${b.available_copies} / ${b.total_copies}</td>
        <td><button class="link-btn" data-remove-book="${escapeHtml(b.id)}">Remove</button></td>
      </tr>`
      )
      .join("");
    tbody.querySelectorAll("[data-remove-book]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api(`/books/${encodeURIComponent(btn.dataset.removeBook)}`, { method: "DELETE" });
          toast("Book removed.");
          loadBooks();
        } catch (e) {
          toast(e.message, true);
        }
      });
    });
  } catch (e) {
    toast(e.message, true);
  }
}

document.getElementById("book-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const payload = {
    id: form.id.value.trim(),
    title: form.title.value.trim(),
    author: form.author.value.trim(),
    genre: form.genre.value.trim() || "General",
    copies: Number(form.copies.value),
  };
  try {
    await api("/books", { method: "POST", body: JSON.stringify(payload) });
    toast("Book added to catalog.");
    form.reset();
    form.copies.value = 1;
    loadBooks();
  } catch (e) {
    toast(e.message, true);
  }
});

let searchTimer;
document.getElementById("book-search").addEventListener("input", (ev) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadBooks(ev.target.value.trim()), 250);
});

// ---------------- Members ----------------
async function loadMembers() {
  const tbody = document.getElementById("members-table-body");
  tbody.innerHTML = `<tr><td colspan="4">Loading&hellip;</td></tr>`;
  try {
    const members = await api("/members");
    if (!members.length) {
      tbody.innerHTML = `<tr><td colspan="4">No members registered yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = members
      .map(
        (m) => `
      <tr>
        <td>${escapeHtml(m.id)}</td>
        <td>${escapeHtml(m.name)}</td>
        <td class="${m.fine > 0 ? "fine-positive" : ""}">$${m.fine.toFixed(2)}</td>
        <td>
          <div class="pay-row">
            <input type="number" min="0" step="0.5" placeholder="0.00" data-pay-amount="${escapeHtml(m.id)}">
            <button class="pay-btn" data-pay-btn="${escapeHtml(m.id)}">Pay</button>
          </div>
        </td>
      </tr>`
      )
      .join("");
    tbody.querySelectorAll("[data-pay-btn]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.payBtn;
        const input = tbody.querySelector(`[data-pay-amount="${CSS.escape(id)}"]`);
        const amount = Number(input.value);
        if (!amount || amount <= 0) {
          toast("Enter an amount greater than 0.", true);
          return;
        }
        try {
          const r = await api(`/members/${encodeURIComponent(id)}/pay`, {
            method: "POST",
            body: JSON.stringify({ amount }),
          });
          toast(`Payment recorded. Remaining: $${r.remaining_fine.toFixed(2)}`);
          loadMembers();
        } catch (e) {
          toast(e.message, true);
        }
      });
    });
  } catch (e) {
    toast(e.message, true);
  }
}

document.getElementById("member-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const payload = { id: form.id.value.trim(), name: form.name.value.trim() };
  try {
    await api("/members", { method: "POST", body: JSON.stringify(payload) });
    toast("Member registered.");
    form.reset();
    loadMembers();
  } catch (e) {
    toast(e.message, true);
  }
});

// ---------------- Circulation ----------------
function showCirculationMessage(text, isError) {
  const el = document.getElementById("circulation-message");
  el.textContent = text;
  el.className = "message " + (isError ? "error" : "ok");
  el.hidden = false;
}

document.getElementById("issue-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const payload = { member_id: form.member_id.value.trim(), book_id: form.book_id.value.trim() };
  try {
    const r = await api("/issue", { method: "POST", body: JSON.stringify(payload) });
    showCirculationMessage(`${r.message} Due back ${r.due_date}.`, false);
    form.reset();
  } catch (e) {
    showCirculationMessage(e.message, true);
  }
});

document.getElementById("return-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const payload = { member_id: form.member_id.value.trim(), book_id: form.book_id.value.trim() };
  try {
    const r = await api("/return", { method: "POST", body: JSON.stringify(payload) });
    showCirculationMessage(r.message, false);
    form.reset();
  } catch (e) {
    showCirculationMessage(e.message, true);
  }
});

// ---------------- History ----------------
async function loadHistory() {
  const tbody = document.getElementById("history-table-body");
  tbody.innerHTML = `<tr><td colspan="6">Loading&hellip;</td></tr>`;
  try {
    const rows = await api("/transactions");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="6">No circulation history yet.</td></tr>`;
      return;
    }
    const today = new Date().toISOString().slice(0, 10);
    tbody.innerHTML = rows
      .map((t) => {
        let badge = `<span class="badge returned">Returned</span>`;
        if (!t.returned) {
          badge = t.due_date < today ? `<span class="badge overdue">Overdue</span>` : `<span class="badge active">Active</span>`;
        }
        return `
        <tr>
          <td>${escapeHtml(t.member_name)}</td>
          <td>${escapeHtml(t.book_title)}</td>
          <td>${t.issue_date}</td>
          <td>${t.due_date}</td>
          <td>${t.return_date || "&mdash;"}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------- Utils ----------------
function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------------- Init ----------------
loadStats();
