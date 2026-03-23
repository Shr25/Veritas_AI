console.log("popup.js loaded");

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded");

    const btn = document.getElementById("btn");
    const output = document.getElementById("out");

    if (!btn) {
        console.log("Button not found");
        return;
    }

    btn.addEventListener("click", async () => {
        console.log("Button clicked");

        const inputText = document.getElementById("input").value;

        if (!inputText) {
            output.innerHTML = "Please enter a claim";
            return;
        }

        output.innerHTML = "Checking...";

        try {
            console.log("Sending request...");

            const res = await fetch("https://axlike-marcelle-systaltic.ngrok-free.dev/api/check", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text: inputText })
            });

            console.log("Response received");

            const data = await res.json();
            console.log("Data:", data);

            displayResults(data.results);

        } catch (err) {
            console.error("Fetch error:", err);
            output.innerHTML = "Error connecting to backend";
        }
    });

    function displayResults(results) {
        if (!results || results.length === 0) {
            output.innerHTML = "No results found";
            return;
        }

        let html = "";

        results.forEach(r => {
            html += `
                <div class="card">
                    <b>Claim:</b> ${r.claim}<br>
                    <b>Verdict:</b> ${r.analysis?.verdict || "N/A"}<br>
                    <b>Reason:</b> ${r.analysis?.reason || "N/A"}<br>
                    <b>Source:</b> ${r.source_type}<br>
                </div>
            `;
        });

        output.innerHTML = html;
    }
});