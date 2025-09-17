// frontend-app/pages/index.js

const OWNER = "zerradwan";
const REPO = "MarketJournal";
const BRANCH = "main";
const RAW_CSV_URL = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/data/etf_prices_log.csv`;

export async function getServerSideProps() {
  try {
    const res = await fetch(RAW_CSV_URL, { cache: "no-store" });
    if (!res.ok) {
      return { props: { headers: [], rows: [], error: `Fetch failed: ${res.status}` } };
    }

    const csv = (await res.text()).trim();
    if (!csv) return { props: { headers: [], rows: [], error: "CSV empty" } };

    const lines = csv.split(/\r?\n/).filter(Boolean);
    const headers = lines[0].split(",").map((s) => s.trim());

    const rows = lines.slice(1).map((line) => {
      const cols = line.split(",").map((s) => s.trim());
      const obj = {};
      headers.forEach((h, i) => (obj[h] = cols[i] ?? ""));
      return obj;
    });

    // sort by date ascending (oldest → newest)
    rows.sort((a, b) => new Date(a.date) - new Date(b.date));

    return { props: { headers, rows, error: null } };
  } catch (e) {
    return { props: { headers: [], rows: [], error: e?.message || "Unknown error" } };
  }
}

export default function Home({ headers, rows, error }) {
  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: 36, marginBottom: 8 }}>Market Journal</h1>
      <p style={{ marginBottom: 20, color: "#555" }}>
        This website was developed by <strong>Neel Dutta Gupta</strong> and <strong>Zain Radwan</strong>, 
        inspired by <strong>Malachy Odonnabhain</strong>.
      </p>


      {error && <p style={{ color: "crimson", marginBottom: 12 }}>Error: {error}</p>}

      <div style={{ overflowX: "auto", border: "1px solid #e5e7eb", borderRadius: 8 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead style={{ background: "#f9fafb" }}>
            <tr>
              {headers.map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={headers.length} style={{ padding: 12, textAlign: "center", color: "#888" }}>
                  No data yet. Ensure the CSV exists at <code>data/etf_prices_log.csv</code>.
                </td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={i} style={{ borderTop: "1px solid #f0f0f0" }}>
                  {headers.map((h) => (
                    <td key={h} style={{ padding: "8px 8px" }}>
                      {r[h] ?? "—"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
