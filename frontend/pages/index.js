import { useEffect, useState } from "react";
import Papa from "papaparse";

export default function Home() {
  const [data, setData] = useState([]);

  useEffect(() => {
    Papa.parse("/data/etf_prices_log.csv", {
      download: true,
      header: true,
      complete: (results) => setData(results.data),
    });
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h1>Market Journal</h1>
      <table border="1" cellPadding="5">
        <thead>
          <tr>
            <th>Date</th>
            <th>Ticker</th>
            <th>Close</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              <td>{row.Date}</td>
              <td>{row.Ticker}</td>
              <td>{row.Close}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
