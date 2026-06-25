# Especificação de Design do Sistema (Portal Logístico Expresso Neves)

Este documento estabelece as diretrizes de design, a identidade visual e as especificações de engenharia de UI/UX adotadas no projeto **Novo_FrontEnd**. O portal opera com uma interface reativa, de alta performance e apelo visual premium, projetada especificamente para o fluxo de trabalho de despacho e controle logístico urbano.

---

## 1. Visão Geral da Linguagem Visual

O portal utiliza uma linguagem visual híbrida. O shell de navegação e os painéis de radar em tempo real adotam um **modo escuro profundo (Dark Mode)**, reduzindo a fadiga visual dos despachantes e gerando um aspecto operacional de alta tecnologia (estilo "Torre de Controle"). Em contrapartida, as áreas de trabalho contábeis, planilhas e formulários utilizam um **modo claro ultra-limpo (High-Contrast Light Mode)**, garantindo legibilidade máxima durante a auditoria de números e dados contábeis.

A interface faz uso de:
- **Glassmorphism sutil (Glastemismo):** Painéis translúcidos e bordas suaves que dividem o espaço de forma elegante.
- **Micro-animações baseadas em física:** Transições fluidas para aberturas de gavetas laterais (drawers) e modais, implementadas via *Framer Motion*.
- **Foco em Densidade de Informação:** Layout otimizado para expor dados operacionais críticos de forma compacta (tamanho de fonte padrão otimizado de `13px` a `14px`).

---

## 2. Diretrizes de Cores e Temas

O sistema de cores do portal foi desenvolvido sobre a paleta padrão do Tailwind CSS v4, enriquecido com tons de destaque personalizados para o ecossistema Expresso Neves.

### A. Cor de Destaque da Marca (Accent Color)
*   **Laranja Branded:** `#E55C00`
    *   **Propósito:** Representa velocidade, logística ativa e dinamismo. Utilizado em botões de ação primária, anéis de foco ativos, ícones de status dinâmicos e nas linhas de destaque dos gráficos de evolução contábil.
    *   **Classes de estilo:** `text-[#E55C00]`, `bg-[#E55C00]`, `hover:bg-[#c44e00]`, `focus-visible:ring-[#E55C00]`, `activeDot={{ fill: "#E55C00", stroke: "#FFE7D6" }}`.

### B. Cores de Interface do Modo Escuro (Sidebar & Radar)
*   **Background Principal do Menu:** `#0a0a0a` (Preto puro/carvão)
*   **Background de Itens em Hover:** `#151515` (Cinza escuro)
*   **Linhas de Divisão e Bordas Escuras:** `#1a1a1a`
*   **Textos do Menu (Inativos):** `text-zinc-400`
*   **Textos do Menu (Ativos/Destaque):** `text-white`

### C. Cores de Interface do Modo Claro (Espaço de Trabalho)
*   **Background da Tela (Canvas):** `#F9F9FA` (Cinza gelo de alta fidelidade)
*   **Background de Painéis e Cards:** `white` (`#ffffff`)
*   **Bordas Claras Padrão:** `border-zinc-200/80` (bordas semitransparentes) e `border-zinc-100`

### D. Cores de Texto (Tipografia)
*   **Texto Primário:** `text-zinc-900` (`#09090b` - Alto contraste)
*   **Texto Secundário / Legendas:** `text-zinc-500` / `text-zinc-600`
*   **Texto Terciário / Desativado:** `text-zinc-400`

### E. Cores Semânticas de Status
*   **Sucesso / Em Andamento / Ativo:** Verde Esmeralda (`#10B981` / `text-emerald-500` / `bg-emerald-100`) ou Azul Operacional (`#2563eb` / `bg-blue-600` para localizações padrão da empresa no mapa).
*   **Aviso / Atenção / Pendência:** Amarelo Âmbar (`#f59e0b` / `text-amber-500` / `border-amber-500` para destaque de marcadores selecionados no mapa).
*   **Erro / Cancelado / Perigo:** Vermelho/Rosa Carmim (`#rose-700` / `bg-rose-50` / `border-rose-200/70` para mensagens de falha; `#red-600` para modais de exclusão).

---

## 3. Tipografia

A tipografia do projeto foi estruturada para balancear a clareza visual de textos longos com a precisão na leitura de dados numéricos (valores monetários, coordenadas, placas de veículos, documentos).

### A. Famílias de Fontes (Font Families)
*   **Interface e Texto Comum (Sans-Serif):** `"Inter"`, ui-sans-serif, system-ui.
    *   **Propósito:** Legibilidade impecável em telas de alta densidade e tamanhos reduzidos.
*   **Dados Técnicos e Numéricos (Monospace):** `"JetBrains Mono"`, ui-monospace.
    *   **Propósito:** Alinhamento exato de valores numéricos e tabelas operacionais. Utilizado para Placas, IDs de corrida, CNPJ e Coordenadas de GPS.

### B. Escala de Pesos de Fonte (Font Weights)
*   `font-light` (300) - Usada ocasionalmente em descrições secundárias de largura total.
*   `font-normal` (400) - Texto padrão de parágrafos e leituras longas.
*   `font-medium` (500) - Textos informativos de tabelas e rótulos de campos.
*   `font-semibold` (600) - Títulos menores, botões de ação e dados destacados.
*   `font-bold` (700) - Cabeçalhos principais e títulos de painéis.
*   `font-extrabold` (800) - Ações rápidas, badges e indicadores numéricos sintéticos.
*   `font-black` (900) - Valores financeiros consolidados e números principais do Dashboard.

### C. Escala de Tamanhos de Fonte (Font Sizes)
*   `text-[10px]` - Badges de status compactos, indicadores de stepper.
*   `text-[11px]` - Rótulos de abas inativas, texto de rodapé.
*   `text-xs` (12px) - Informações de suporte em formulários, legendas de gráficos.
*   `text-sm` (14px) - Texto de tabelas, botões padrão e inputs.
*   `text-base` (16px) - Títulos de cards e subtítulos operacionais.
*   `text-lg` (18px) - Cabeçalho de modais e painéis de controle.
*   `text-xl` (20px) - Título das páginas e totalizadores numéricos principais.

---

## 4. Sistema de Espaçamento e Grids

O layout e espaçamento do Portal de Despacho seguem uma métrica estrutural rígida baseada em múltiplos de `4px` (`rem` padrão do Tailwind), visando a coesão visual e o alinhamento pixel-perfect.

### A. Margens e Paddings
*   **Margem Externa de Páginas:** `space-y-6` no contêiner principal; cabeçalhos de página com `pb-4 border-b`.
*   **Preenchimento de Painéis (Cards):** `p-5` ou `p-6` (de 20px a 24px) para garantir espaço de respiro nos dados.
*   **Preenchimento de Células de Tabelas:** `px-4 py-3` ou `px-3 py-2.5`.
*   **Espaçamento entre Inputs:** `space-y-4` ou `grid gap-3` para agrupar campos correlacionados.

### B. Estrutura de Layout Responsivo (Breakpoints)
*   `sm` (640px) - Ajuste de grids de cards estatísticos para 2 colunas; botões de modal mudam para layout horizontal.
*   `md` (768px) - Login muda para 2 colunas (Branding lateral + Card de autenticação); textos do sistema sobem para `text-[14px]`. Habilitação de controles extras de cabeçalho.
*   `lg` (1024px) - O menu lateral (sidebar) passa a ser estático e fixado à esquerda. O grid de estatísticas passa para 4 colunas.
*   `xl` (1280px) - Redimensionamento automático de modais de criação rápida e ampliação de visualização de mapas.

---

## 5. Componentes Base de UI

Os componentes visuais do portal foram implementados sem bibliotecas externas pesadas, garantindo leveza técnica e total autonomia sobre os estados visuais.

### A. Botões (Buttons)
*   **Botão Primário (Brand Orange):**
    *   *Estilo:* `bg-[#E55C00] text-white hover:bg-[#c44e00] font-bold rounded-lg shadow-sm`.
    *   *Feedback visual:* Escurece ligeiramente no hover, exibe anel de foco laranja em destaque ao usar teclado (`focus-visible:ring-[#E55C00]`).
*   **Botão Primário de Ação Escura:**
    *   *Estilo:* `bg-zinc-900 text-white hover:bg-zinc-800 font-bold rounded-lg shadow-sm`.
    *   *Uso:* Cadastro rápido, salvar configurações.
*   **Botão Secundário / Cancelar:**
    *   *Estilo:* `border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 font-bold rounded-lg`.
    *   *Uso:* Descarte de alterações, fechamento de modais.
*   **Botão de Perigo (Danger):**
    *   *Estilo:* `bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-sm`.
    *   *Uso:* Confirmações de exclusão de motoboy ou cancelamento irreversível de corrida.

### B. Controles Segmentados (Segmented Controls)
*   *Uso:* Seleção de períodos temporais (Hoje, 7 dias, Mês) ou modos de visualização rápida.
*   *Estilo:* Contêiner com `bg-white border border-zinc-200/80 rounded-xl p-1 shadow-sm`. O botão ativo ganha `bg-[#0a0a0a] text-white shadow` e o inativo usa `text-zinc-600 hover:bg-zinc-50`.

### C. Campos de Formulário (Inputs)
*   **Input de Escrita Padrão:**
    *   *Estilo:* `w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 outline-none transition-all`.
*   **Input de Apenas Leitura (Read-Only Data Display):**
    *   *Estilo:* `w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold cursor-not-allowed`.
    *   *Uso:* Exibição de dados fixados de cadastro de motoboy que não podem ser alterados sem auditoria.

### D. Cards
*   **Glass Panel Card:**
    *   *Estilo:* `.glass-panel` (definido em `index.css`). Aplica `bg-white border border-zinc-200/80 shadow-[0_2px_8px_-2px_rgba(0,0,0,0.05)] rounded-xl`.
*   **Dark Console Card:**
    *   *Estilo:* `bg-[#0a0a0a] border border-[#1a1a1a] text-white rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.12)]`. Possui efeito radial gradiente de fundo (`bg-[#E55C00]/10 blur-[80px]`) para dar profundidade premium.

### E. Modals e Drawers
*   **Modal de Confirmação Centralizado (ex: ConfirmModal):**
    *   *Estrutura:* Fundo semitransparente escuro com efeito blur (`bg-zinc-900/40 backdrop-blur-sm z-[2000]`). O corpo do modal centralizado abre via animação tipo "Spring" (`scale: 0.95 -> 1`).
*   **Drawer Lateral de Ficha (ex: MotoboyModal):**
    *   *Estrutura:* Desliza da direita para a esquerda (`fixed top-0 right-0 h-full w-full max-w-md bg-white border-l`). Utiliza Framer Motion para transição física do eixo X (`initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }}`).

---

## 6. Padrões de Implementação CSS no Tailwind v4

Com o uso do **Tailwind CSS v4**, a configuração visual do tema não está mais dispersa em um arquivo `tailwind.config.js` externo, mas sim estruturada diretamente no ponto de entrada global de estilos (`src/index.css`), utilizando a diretiva `@theme`. 

Isso garante que toda a equipe de engenharia estenda o design system de forma declarativa e centralizada em arquivos CSS puros, otimizando o processo de compilação da build e melhorando a integridade das variáveis CSS nativas em runtime.
