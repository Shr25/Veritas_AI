console.log("popup.js loaded");

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded");

    const btn = document.getElementById("btn");
    const output = document.getElementById("out");
    const inputEl = document.getElementById("input");
    const API_BASE = "http://127.0.0.1:8000";

    if (!btn || !output || !inputEl) {
        console.log("Button or output div not found");
        return;
    }

    async function getActiveTab() {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        return tab;
    }

    async function extractPageText() {
        const tab = await getActiveTab();
        if (!tab?.id) return null;

        const [{ result }] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
                try {
                    const selection = (window.getSelection?.()?.toString() || "").trim();
                    if (selection && selection.length >= 40) return selection;

                    const metaDesc =
                        document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
                        document.querySelector('meta[name="description"]')?.getAttribute("content") ||
                        "";

                    const title =
                        document.querySelector('meta[property="og:title"]')?.getAttribute("content") ||
                        document.title ||
                        "";

                    const root =
                        document.querySelector("article") ||
                        document.querySelector("main") ||
                        document.querySelector('[role="main"]') ||
                        document.body;

                    const paras = Array.from(root?.querySelectorAll?.("p") || [])
                        .map(p => (p.innerText || "").trim())
                        .filter(t => t.length >= 80);

                    // 🔥 TAKE ONLY TOP 2 PARAGRAPHS (UPDATED)
                    const keyParas = paras.slice(0, 2);
                    const combined = keyParas.join(" ").trim();

                    // 🔥 MUCH SMALLER PAYLOAD (UPDATED)
                    const capped = combined.length > 800 ? combined.slice(0, 800) + "…" : combined;

                    const header = [title.trim(), metaDesc.trim()].filter(Boolean).join(" ");
                    const out = [header, capped].filter(Boolean).join(" ").trim();

                    return out || null;
                } catch (e) {
                    return null;
                }
            },
        });

        return result || null;
    }

    async function runCheck(text) {
        console.log("Button clicked");

        const inputText = String(text || "").trim();

        if (!inputText) {
            output.innerHTML = "Please enter a claim";
            return;
        }

        // 🔥 SEND ONLY FIRST SENTENCE (UPDATED)
        const firstSentence = inputText.split(/[.?!]/)[0];

        const steps = [
            "🔍 Extracting claim...",
            "🧠 Understanding context...",
            "🌐 Searching live news...",
            "📚 Fetching research data...",
            "⚖️ Analyzing evidence...",
            "📊 Finalizing verdict..."
        ];

        let stepIndex = 0;
        output.innerHTML = steps[0];

        const interval = setInterval(() => {
            if (stepIndex < steps.length - 1) {
                stepIndex++;
                output.innerHTML = steps[stepIndex];
            }
        }, 400);

        try {
            const res = await fetch(`${API_BASE}/api/check`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                // 🔥 UPDATED HERE
                body: JSON.stringify({ text: firstSentence })
            });

            const data = await res.json();
            const jobId = data.job_id;

            if (data.results) {
                clearInterval(interval);
                displayResults(data.results);
                return;
            }

            if (!jobId) {
                clearInterval(interval);
                output.innerHTML = "Invalid backend response (no job_id/results)";
                return;
            }

            let finalData;
            let attempts = 0;
            let lastStatus = null;

            while (true) {
                const r = await fetch(`${API_BASE}/api/fetch?job_id=${jobId}`);
                finalData = await r.json();

                if (!finalData || Object.keys(finalData).length === 0) {
                    clearInterval(interval);
                    output.innerHTML = "Invalid backend response";
                    return;
                }

                const status = String(finalData.status || "").toLowerCase().trim();

                if (status !== lastStatus) {
                    console.log("STATUS:", status, finalData);
                    lastStatus = status;
                }

                if (status === "done") {
                    console.log("FINAL DATA:", finalData);
                    break;
                }
                // 🔥 SHOW INTERMEDIATE RESULTS IF AVAILABLE
                if (finalData.results && finalData.results.length > 0) {
                    clearInterval(interval);
                    displayResults(finalData.results);
                    return;
                }

                if (status === "error") {
                    clearInterval(interval);
                    output.innerHTML = "Error processing request";
                    return;
                }

                attempts++;

                if (attempts > 600) {
                    clearInterval(interval);
                    output.innerHTML = "Taking too long...";
                    return;
                }

                const delayMs = attempts < 10 ? 250 : attempts < 25 ? 500 : 900;
                await new Promise(res => setTimeout(res, delayMs));
            }

            clearInterval(interval);

            if (finalData.status === "done") {
                output.innerHTML = "Showing results...";
                displayResults(finalData.results);
            } else {
                output.innerHTML = "Processing...";
            }

        } catch (err) {
            clearInterval(interval);
            console.error("Fetch error:", err);
            output.innerHTML = "Error connecting to backend";
        }
    }

    btn.addEventListener("click", async () => {
        await runCheck(inputEl.value);
    });

    (async () => {
        try {
            if (String(inputEl.value || "").trim()) return;
            const pageText = await extractPageText();
            if (!pageText) return;
            inputEl.value = pageText;
            await runCheck(pageText);
        } catch (e) {
        }
    })();

    function displayResults(results) {
        if (!results || results.length === 0) {
            output.innerHTML = "No results found";
            return;
        }

        let html = "";

        results.forEach(r => {
            html += `
                <div class="card">
                    <div class="claim"><b>Claim:</b> ${r.claim}</div>
                    <div>
                        <b>Verdict:</b>
                        <span class="verdict ${
                            (r.analysis?.verdict || "").toLowerCase().includes("true") ? "true" :
                            (r.analysis?.verdict || "").toLowerCase().includes("false") ? "false" :
                            "neutral"
                        }">
                            ${r.analysis?.verdict || "N/A"} 
                        </span>
                    </div>
                    <div class="reason">
                        <b>Reason:</b><br>
                        ${r.analysis?.reason || "N/A"}
                    </div>
                    <div class="source">
                        Source: ${r.source_type}
                    </div>
                </div>
            `;
        }
        );

        output.innerHTML = html;
    }
});