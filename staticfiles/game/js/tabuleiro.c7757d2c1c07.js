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

  // ----- util: rolar a coluna do log até o final (mais recente embaixo) -----
  function scrollLogBottom() {
    const logDiv = document.querySelector(".log-coluna");
    if (logDiv) logDiv.scrollTop = logDiv.scrollHeight;
  }

  // ----- pinos -----
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
  // garante que ao carregar a página o log já esteja no fim
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

  function desenharLigacao(inicio, fim, classe, comDegraus = false) {
    const r = grid.getBoundingClientRect();
    const c1 = centroDaCasa(inicio);
    const c2 = centroDaCasa(fim);
    const x1 = c1.x * r.width, y1 = c1.y * r.height;
    const x2 = c2.x * r.width, y2 = c2.y * r.height;

    // Linha base
    const path = document.createElementNS("http://www.w3.org/2000/svg", "line");
    path.setAttribute("x1", x1); path.setAttribute("y1", y1);
    path.setAttribute("x2", x2); path.setAttribute("y2", y2);
    path.setAttribute("class", classe);
    svg.appendChild(path);

    if (comDegraus) {
      // Degraus ao longo da escada
      const degraus = 4;
      for (let i = 1; i <= degraus; i++) {
        const t = i / (degraus + 1);
        const xd = x1 + (x2 - x1) * t;
        const yd = y1 + (y2 - y1) * t;
        // segmento curto perpendicular
        const vx = x2 - x1, vy = y2 - y1;
        const len = Math.hypot(vx, vy) || 1;
        const nx = -vy / len, ny = vx / len;
        const half = 10;
        const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
        l.setAttribute("x1", xd - nx * half);
        l.setAttribute("y1", yd - ny * half);
        l.setAttribute("x2", xd + nx * half);
        l.setAttribute("y2", yd + ny * half);
        l.setAttribute("class", classe + " degrau");
        svg.appendChild(l);
      }
    }
  }

  // ----- animação passo-a-passo -----
  function animarMovimento(ultMov, callback) {
    if (!ultMov) { callback && callback(); return; }
    const { jogador, de, para, pre_salto } = ultMov;

    // etapa 1: caminha casa-a-casa até o destino bruto (ou final se não houver salto)
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
          // pequena pausa e "salta" para a casa final
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

  // Redesenha SVG e animações somente depois do layout estar pronto
  function desenharTudoEAniMar() {
    atualizarViewBoxSVG();
    limparSVG();

    // Escadas (verde) e cobras (vermelho)
    Object.entries(ESCADAS).forEach(([ini, fim]) => {
      desenharLigacao(parseInt(ini, 10), parseInt(fim, 10), "escada", true);
    });
    Object.entries(COBRAS).forEach(([cabeca, cauda]) => {
      desenharLigacao(parseInt(cabeca, 10), parseInt(cauda, 10), "cobra", false);
    });

    // Anima o último movimento; se a vez for da máquina, joga sozinha
    animarMovimento(ULT, () => {
      // após animar, garante que o log está rolado para o final
      scrollLogBottom();

      if (STATUS !== "finalizado" && JOG_ATUAL !== 0) {
        const form = document.getElementById("form-jogar");
        setTimeout(() => form && form.submit(), 400);
      }
    });
  }

  // Primeiro frame após o layout: desenha tudo
  requestAnimationFrame(desenharTudoEAniMar);

  // Se a janela for redimensionada, recalcule o SVG (com um pequeno debounce)
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      requestAnimationFrame(() => {
        desenharTudoEAniMar();
        // e mantenha o log ancorado no fim
        scrollLogBottom();
      });
    }, 120);
  });

    window.Tabuleiro = {
    // Atualiza as posições e redesenha os pinos (sem animação de caminho):
    setPositions(arr) {
      if (!Array.isArray(arr)) return;
      // mantém o mesmo array (para não quebrar referências internas)
      POSICOES.length = 0;
      for (let i = 0; i < arr.length; i++) POSICOES.push(arr[i] | 0);
      desenharPinos(POSICOES);
    },

    // Anima um movimento no mesmo estilo do single-player:
    // payload: { jogador, de, para, pre_jump | pre_salto }
    animateMove(payload) {
      if (!payload) return;
      const ult = {
        jogador: payload.jogador | 0,
        de:      payload.de | 0,
        para:    payload.para | 0,
        pre_salto: (payload.pre_jump ?? payload.pre_salto ?? null)
      };
      animarMovimento(ult, () => {});
    },

    // Força um redesenho completo (útil após resize dinâmico):
    redraw() {
      desenharTudoEAniMar();
    }
  };

})();
