// One live connection to the hub for every open view (a shared worker): browsers allow six connections to one address,
// and each open view (Deck, Profiles, 3D, Chronology, the hub page) holding its own would use them up, after which every
// other request waits (Ben, 29 October: "now nothing works"). The worker keeps one EventSource and relays it to each tab.
const ports = new Set();
let es = null, state = 'connecting';
const send = (m) => { for (const p of ports) { try { p.postMessage(m); } catch (e) { ports.delete(p); } } };
function connect() {
  es = new EventSource('/api/events');
  es.onopen = () => { state = 'open'; send({ kind: 'open' }); };
  es.onmessage = (m) => send({ kind: 'msg', data: m.data });
  es.onerror = () => { state = 'error'; send({ kind: 'error' }); };
}
onconnect = (e) => {
  const p = e.ports[0]; ports.add(p);
  p.onmessage = (m) => { if (m.data === 'bye') ports.delete(p); };
  p.start();
  if (!es) connect(); else p.postMessage({ kind: state === 'open' ? 'open' : state });
};
