(function () {
  const byId = (id) => document.getElementById(id);

  // Helper robusto: lê JSON de <script type="application/json"> com fallback
  function getJSON(id, fallback) {
    const el = byId(id);
    if (!el) return fallback;
    try {
      const txt = (el.textContent || "").trim();
      if (!txt) return fallback;
      return JSON.parse(txt);
    } catch (e) {
      console.warn("Falha ao parsear", id, e);
      return fallback;
    }
  }

  const grid = byId("tabuleiro");
  if (!grid) return;

  const ROWS = parseInt(grid.dataset.linhas, 10) || 10;
  const COLS = parseInt(grid.dataset.colunas, 10) || 10;

  // Lê dados do backend com segurança
  const POSICOES   = getJSON("js-posicoes", []);
  const COBRAS     = getJSON("js-cobras", {});
  const ESCADAS    = getJSON("js-escadas", {});
  const ULT        = getJSON("js-ultimo-mov", null);
  const STATUS     = getJSON("js-status", "andamento");
  const JOG_ATUAL  = getJSON("js-jogador-atual", 0);
  const CASA_FINAL = getJSON("js-casa-final", 100);

  // Garante o grid CSS
  grid.style.gridTemplateColumns = `repeat(${COLS}, 1fr)`;
  grid.style.gridTemplateRows    = `repeat(${ROWS}, 1fr)`;

  // ----- cria células (somente se NÃO existirem) -----
  if (!grid.querySelector(".celula")) {
    const frag = document.createDocumentFragment();
    for (let visualRow = 0; visualRow < ROWS; visualRow++) {
      const rowFromBottom = ROWS - 1 - visualRow; // 0 = linha de baixo
      const even = rowFromBottom % 2 === 0;

      for (let col = 0; col < COLS; col++) {
        const cellNumber = even
          ? rowFromBottom * COLS + (col + 1)
          : rowFromBottom * COLS + (COLS - col);

        const cell = document.createElement("div");
        cell.className = "celula";
        cell.dataset.casa = String(cellNumber);
        cell.innerHTML = `<span class="numero">${cellNumber}</span><div class="pinos"></div>`;
        frag.appendChild(cell);
      }
    }
    grid.appendChild(frag);
  }

  // destaca visualmente a casa final (100 ou 25)
  const finalCellEl = grid.querySelector(`.celula[data-casa="${CASA_FINAL}"]`);
  if (finalCellEl) {
    finalCellEl.classList.add("celula-final");
  }

  // ----- util: rolar a coluna do log até o final (mais recente embaixo) -----
  function scrollLogBottom() {
    const logDiv = document.querySelector(".log-coluna");
    if (logDiv) logDiv.scrollTop = logDiv.scrollHeight;
  }

  // ----- pinos/peões -----
  function desenharPinos(positions) {
    grid.querySelectorAll(".pinos").forEach((p) => (p.innerHTML = ""));
    positions.forEach((pos, idx) => {
      const casa = pos === 0 ? 1 : pos; // 0 fica visualmente na casa 1
      const alvo = grid.querySelector(`.celula[data-casa="${casa}"] .pinos`);
      if (alvo) {
        const pin = document.createElement("span");
        pin.className = `pino pino-${idx + 1}`;
        pin.title = `Jogador ${idx + 1}`;
        pin.textContent = String(idx + 1);
        alvo.appendChild(pin);
      }
    });
  }
  desenharPinos(POSICOES);
  scrollLogBottom();

  // ----- SVG (cobras/escadas) -----
  const svg = byId("camada-svg");

  function centroDaCasa(n) {
    const el = grid.querySelector(`.celula[data-casa="${n}"]`);
    if (!el) return { x: 0, y: 0 };
    const rect = el.getBoundingClientRect();
    const gridRect = grid.getBoundingClientRect();
    const cx = (rect.left + rect.width / 2 - gridRect.left) / gridRect.width;
    const cy = (rect.top + rect.height / 2 - gridRect.top) / gridRect.height;
    return { x: cx, y: cy };
  }

  function atualizarViewBoxSVG() {
    const r = grid.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${r.width} ${r.height}`);
    svg.setAttribute("width", r.width);
    svg.setAttribute("height", r.height);
  }

  function limparSVG() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
  }

  // desenha cobras e escadas
  function desenharLigacao(inicio, fim, classe, comDegraus = false) {
    const r = grid.getBoundingClientRect();
    const c1 = centroDaCasa(inicio);
    const c2 = centroDaCasa(fim);
    const x1 = c1.x * r.width, y1 = c1.y * r.height;
    const x2 = c2.x * r.width, y2 = c2.y * r.height;

    /* COBRA: corpo curvo */
    if (classe === "cobra") {
      const vx = x2 - x1;
      const vy = y2 - y1;
      const len = Math.hypot(vx, vy) || 1;
      const dx = vx / len;
      const dy = vy / len;
      const nx = -dy;
      const ny = dx;

      const midX = (x1 + x2) / 2;
      const midY = (y1 + y2) / 2;
      const amplitude = Math.min(80, len * 0.25);

      const cx = midX + nx * amplitude;
      const cy = midY + ny * amplitude;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`);
      path.setAttribute("class", "cobra");
      svg.appendChild(path);

      return;
    }

    /* ESCADA: dois trilhos paralelos + degraus */
    if (classe === "escada") {
      const vx = x2 - x1;
      const vy = y2 - y1;
      const len = Math.hypot(vx, vy) || 1;
      const dx = vx / len;
      const dy = vy / len;
      const nx = -dy;
      const ny = dx;

      const railOffset = 10;     // distância entre os trilhos / 2
      const steps      = 5;      // número de degraus

      // função helper pra criar linhas
      function line(xa, ya, xb, yb, className) {
        const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
        l.setAttribute("x1", xa);
        l.setAttribute("y1", ya);
        l.setAttribute("x2", xb);
        l.setAttribute("y2", yb);
        l.setAttribute("class", className);
        svg.appendChild(l);
      }

      // trilho esquerdo e direito
      const leftStartX  = x1 + nx * railOffset;
      const leftStartY  = y1 + ny * railOffset;
      const leftEndX    = x2 + nx * railOffset;
      const leftEndY    = y2 + ny * railOffset;

      const rightStartX = x1 - nx * railOffset;
      const rightStartY = y1 - ny * railOffset;
      const rightEndX   = x2 - nx * railOffset;
      const rightEndY   = y2 - ny * railOffset;

      line(leftStartX,  leftStartY,  leftEndX,  leftEndY,  "escada");
      line(rightStartX, rightStartY, rightEndX, rightEndY, "escada");

      // degraus ligando um trilho ao outro
      if (comDegraus) {
        for (let i = 1; i <= steps; i++) {
          const t = i / (steps + 1); // espalha os degraus ao longo da escada

          // ponto central do degrau no meio do segmento principal
          const cx = x1 + (x2 - x1) * t;
          const cy = y1 + (y2 - y1) * t;

          const startX = cx + nx * railOffset;
          const startY = cy + ny * railOffset;
          const endX   = cx - nx * railOffset;
          const endY   = cy - ny * railOffset;

          line(startX, startY, endX, endY, "escada degrau");
        }
      }
      return;
    }

    // fallback: caso acontecer algum erro/problema, desenha uma linha simples
    const main = document.createElementNS("http://www.w3.org/2000/svg", "line");
    main.setAttribute("x1", x1);
    main.setAttribute("y1", y1);
    main.setAttribute("x2", x2);
    main.setAttribute("y2", y2);
    main.setAttribute("class", classe);
    svg.appendChild(main);

    if (comDegraus) {
      const degraus = 4;
      for (let i = 1; i <= degraus; i++) {
        const t = i / (degraus + 1);
        const xd = x1 + (x2 - x1) * t;
        const yd = y1 + (y2 - y1) * t;
        const vx2 = x2 - x1, vy2 = y2 - y1;
        const len2 = Math.hypot(vx2, vy2) || 1;
        const nx2 = -vy2 / len2, ny2 = vx2 / len2;
        const half = 10;

        const rung = document.createElementNS("http://www.w3.org/2000/svg", "line");
        rung.setAttribute("x1", xd - nx2 * half);
        rung.setAttribute("y1", yd - ny2 * half);
        rung.setAttribute("x2", xd + nx2 * half);
        rung.setAttribute("y2", yd + ny2 * half);
        rung.setAttribute("class", classe + " degrau");
        svg.appendChild(rung);
      }
    }
  }


  // ----- animação passo-a-passo -----
  function animarMovimento(ultMov, callback) {
    if (!ultMov) { callback && callback(); return; }
    const { jogador, de, para, pre_salto } = ultMov;

    const destinoEtapa1 = (pre_salto ?? para);
    const caminho1 = [];
    if (destinoEtapa1 > de) {
      for (let k = de + 1; k <= destinoEtapa1; k++) caminho1.push(k);
    }

    const teveSalto = pre_salto !== null && pre_salto !== undefined && pre_salto !== para;
    const delay = 220; // ms entre casas
    let idx = 0;

    function passo1() {
      if (idx >= caminho1.length) {
        if (teveSalto) {
          setTimeout(() => {
            POSICOES[jogador] = para;
            desenharPinos(POSICOES);
            callback && callback();
          }, 250);
        } else {
          callback && callback();
        }
        return;
      }
      POSICOES[jogador] = caminho1[idx];
      desenharPinos(POSICOES);
      idx++;
      setTimeout(passo1, delay);
    }
    passo1();
  }

  function desenharTudoEAniMar() {
    atualizarViewBoxSVG();
    limparSVG();

    // Escadas (verde) e cobras (laranja curva)
    Object.entries(ESCADAS).forEach(([ini, fim]) => {
      desenharLigacao(parseInt(ini, 10), parseInt(fim, 10), "escada", true);
    });
    Object.entries(COBRAS).forEach(([cabeca, cauda]) => {
      desenharLigacao(parseInt(cabeca, 10), parseInt(cauda, 10), "cobra", false);
    });

    animarMovimento(ULT, () => {
      scrollLogBottom();

      if (STATUS !== "finalizado" && JOG_ATUAL !== 0) {
        const form = document.getElementById("form-jogar");
        setTimeout(() => form && form.submit(), 400);
      }
    });
  }

  requestAnimationFrame(desenharTudoEAniMar);

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      requestAnimationFrame(() => {
        desenharTudoEAniMar();
        scrollLogBottom();
      });
    }, 120);
  });

  window.Tabuleiro = {
    setPositions(arr) {
      if (!Array.isArray(arr)) return;
      POSICOES.length = 0;
      for (let i = 0; i < arr.length; i++) POSICOES.push(arr[i] | 0);
      desenharPinos(POSICOES);
    },

    // payload: { jogador, de, para, pre_jump | pre_salto }
    animateMove(payload, onDone) {
      if (!payload) {
        if (typeof onDone === "function") onDone();
        return;
      }
      const ult = {
        jogador: payload.jogador | 0,
        de:      payload.de | 0,
        para:    payload.para | 0,
        pre_salto: (payload.pre_jump ?? payload.pre_salto ?? null)
      };
      animarMovimento(ult, function () {
        if (typeof onDone === "function") onDone();
      });
    },
  };

})();
