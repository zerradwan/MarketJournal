// Simple Next.js page that fetches the CSV from GitHub and renders a table.
// Deploy the "frontend" folder to Vercel (project root at /frontend).

import { useMemo } from "react";

// Adjust these to your repo path/branch
const OWNER = "zerradwan";        // or your org/user
const REPO  = "MarketJournal";    // repo name
const BRANCH = "main";
const RAW_CSV_URL =
  `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/data/etf_prices_log.csv`;

export async function getServerSideProps() {
  try {
    const r = await fetch(RAW_CSV_URL, { cache: "no-store" });
    if (!r.ok) throw new Error(`Failed to fetch CSV: ${r.status}`);
    const csv = await r.text();
    return { props: { csv } };
  } catch (e) {
    return { props: { csv: "", error: e?.message || "Fetch error" } };
  }
}

function parseCSV(csv) {
  if (!csv) return { headers: [], rows: [] };
  const lines = csv.trim().split(/\r?\n/);
  if (lines.length < 2) return { headers: [], rows: [] };
  const headers = lines[0].split(",").map((s) => s.trim());
  const rows = lines.slice(1).map((line) => {
    const cols = line.split(",").map((s) => s.trim());
    const obj = {};
    headers.forEach((h, i) => (obj[h] = cols[i]));
    return obj;
  });
  // newest first (CSV appends daily at bottom; reverse for display)
  rows.reverse();
  return { headers, rows };
}

export default function Home({ csv, error }) {
  const { headers, rows } = useMemo(() => parseCSV(csv), [csv]);

  const fields = [
    "EURO/USD","STG/USD","USD/YEN",
    "NIKKEI","DAX","FTSE","DOW","S&P",
    "JAPAN 10 YR (%)","GERMAN 10 YR (%)","UK 10 YR (%)","US 10 YR (%)",
    "GOLD","BRENT CRUDE","BITCOIN"
  ];

  return (
    <main style={{maxWidth: 1100, margin: "0 auto", padding: 24}}>
      <h1 style={{fontSize: 24, fontWeight: 700, marginBottom: 8}}>Daily Market Journal</h1>
      {error && <p style={{color: "crimson"}}>Error: {error}</p>}
      <p style={{color: "#555", marginBottom: 16}}>
        Data source: GitHub CSV (auto-updated by GitHub Actions)
      </p>

      <div style={{overflowX: "auto", border: "1px solid #eee", borderRadius: 8}}>
        <table style={{width: "100%", fontSize: 14, borderCollapse: "collapse"}}>
          <thead style={{background: "#f9fafb"}}>
            <tr>
              <th style={{textAlign: "left", padding: 8}}>Date</th>
              {fields.map((f) => (
                <th key={f} style={{textAlign: "right", padding: 8}}>{f}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{borderTop: "1px solid #eee"}}>
                <td style={{padding: 8}}>{r.date}</td>
                {fields.map((f) => (
                  <td key={f} style={{padding: 8, textAlign: "right"}}>
                    {r[f] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p style={{fontSize: 12, color: "#777", marginTop: 12}}>
        Yahoo Finance (FX, indices, gold, Brent), FRED (10Y yields), CoinGecko (BTC).
      </p>
    </main>
  );
}
