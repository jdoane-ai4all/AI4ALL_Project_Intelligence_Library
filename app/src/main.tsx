import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import DataLoader from "./components/DataLoader";
import "./styles.css";
import type { Library } from "./types";

const root = createRoot(document.getElementById("root")!);
const show = (lib: Library) => root.render(<React.StrictMode><App lib={lib} /></React.StrictMode>);

// Data sources, in order: the Streamlit wrapper embeds it as window.__AIPIL_LIBRARY__; a local/private build serves
// ./data/library.json; otherwise (e.g. the public GitHub Pages build) the viewer opens their own copy in the browser.
const embedded = (window as unknown as { __AIPIL_LIBRARY__?: Library }).__AIPIL_LIBRARY__;
(embedded ? Promise.resolve(embedded) : fetch("./data/library.json").then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }))
  .then(show)
  .catch((e) => {
    console.info("No bundled data; asking the viewer to open library.json.", e);
    root.render(<DataLoader onLoad={show} />);
  });
