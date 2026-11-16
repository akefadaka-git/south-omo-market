const workQueues = [
  { title: 'Listings awaiting review', count: 'Not connected' },
  { title: 'Open safety reports', count: 'Not connected' },
  { title: 'Seller accounts', count: 'Not connected' },
];

export default function App() {
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', margin: '3rem auto', maxWidth: 900, padding: 24 }}>
      <p style={{ color: '#356859', fontWeight: 700 }}>SOUTH OMO MARKET</p>
      <h1>Administration</h1>
      <p>Moderation workspace foundation. No live marketplace data is connected.</p>
      <section style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        {workQueues.map((item) => (
          <article key={item.title} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20 }}>
            <h2 style={{ fontSize: 18 }}>{item.title}</h2><p>{item.count}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
