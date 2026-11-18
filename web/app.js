const form = document.querySelector("#recommend-form");
const queryInput = document.querySelector("#query");
const promptCount = document.querySelector("#prompt-count");
const statusCard = document.querySelector("#status-card");
const resultsList = document.querySelector("#results-list");
const resultsTitle = document.querySelector("#results-title");
const resultCount = document.querySelector("#result-count");
const interpretation = document.querySelector("#interpretation");
const retrievalQuery = document.querySelector("#retrieval-query");
const preferenceChips = document.querySelector("#preference-chips");
const toast = document.querySelector("#toast");
const audio = document.querySelector("#audio-element");
const playButton = document.querySelector("#play-button");
const waveform = document.querySelector("#waveform");
const playerTitle = document.querySelector("#player-title");
const playerArtist = document.querySelector("#player-artist");
const playerStatus = document.querySelector("#player-status");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3600);
}

function setLoading(isLoading) {
  const button = form.querySelector(".primary-button");
  button.disabled = isLoading;
  button.querySelector("span:first-child").textContent = isLoading ? "Finding your sound..." : "Find my sound";
  statusCard.classList.remove("is-hidden");
  statusCard.innerHTML = isLoading
    ? '<span class="status-orb is-loading" aria-hidden="true"></span><div><strong>Listening closely...</strong><p>Gemini is shaping your brief, then the catalog is being ranked.</p></div>'
    : statusCard.innerHTML;
}

function renderInterpretation(data) {
  interpretation.classList.remove("is-hidden");
  retrievalQuery.textContent = `“${data.retrieval_query}”`;
  const preferenceEntries = Object.entries(data.preferences);
  const chips = [...preferenceEntries.map(([key, value]) => `${key.replaceAll("_", " ")} · ${value}`), ...data.keywords];
  preferenceChips.innerHTML = chips.map((chip) => `<span class="chip">${escapeHtml(chip)}</span>`).join("");
}

function renderResults(results) {
  statusCard.classList.add("is-hidden");
  resultsList.classList.remove("is-hidden");
  resultsTitle.textContent = "A set shaped for you";
  resultCount.textContent = `${results.length} tracks`;
  resultsList.innerHTML = results.map((result, index) => `
    <article class="song-row" style="animation-delay: ${index * 45}ms" data-index="${index}">
      <span class="song-number">${String(index + 1).padStart(2, "0")}</span>
      <div class="song-main">
        <div class="song-title">${escapeHtml(result.title)}</div>
        <div class="song-artist">${escapeHtml(result.artist)}</div>
      </div>
      <span class="song-genre">${escapeHtml(result.genre)}</span>
      <span class="song-score">${Number(result.score).toFixed(3)}</span>
      <button class="song-action" type="button" aria-label="Select ${escapeHtml(result.title)}">▶</button>
      <div class="song-reason">${escapeHtml(result.reason)}</div>
    </article>
  `).join("");
  resultsList._results = results;
  selectTrack(results[0]);
}

function selectTrack(track) {
  if (!track) return;
  playerTitle.textContent = track.title;
  playerArtist.textContent = track.artist;
  audio.pause();
  waveform.classList.remove("is-playing");

  if (track.audio_url) {
    audio.src = track.audio_url;
    playButton.disabled = false;
    playerStatus.textContent = "Preview ready";
  } else {
    audio.removeAttribute("src");
    audio.load();
    playButton.disabled = true;
    playerStatus.textContent = "No preview URL in the current catalog";
  }
}

queryInput.addEventListener("input", () => {
  promptCount.textContent = `${queryInput.value.length} / 240`;
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query;
    queryInput.dispatchEvent(new Event("input"));
    queryInput.focus();
  });
});

resultsList.addEventListener("click", (event) => {
  const row = event.target.closest(".song-row");
  if (!row || !resultsList._results) return;
  selectTrack(resultsList._results[Number(row.dataset.index)]);
});

playButton.addEventListener("click", async () => {
  if (audio.paused) {
    await audio.play();
    waveform.classList.add("is-playing");
    playButton.textContent = "Ⅱ";
  } else {
    audio.pause();
    waveform.classList.remove("is-playing");
    playButton.textContent = "▶";
  }
});

audio.addEventListener("ended", () => {
  waveform.classList.remove("is-playing");
  playButton.textContent = "▶";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  setLoading(true);
  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The recommendation request failed.");
    renderInterpretation(data);
    renderResults(data.results);
  } catch (error) {
    resultsList.classList.add("is-hidden");
    statusCard.classList.remove("is-hidden");
    statusCard.innerHTML = `<span class="status-orb" aria-hidden="true"></span><div><strong>We could not shape that set.</strong><p>${escapeHtml(error.message)}</p></div>`;
    showToast(error.message);
  } finally {
    setLoading(false);
  }
});
