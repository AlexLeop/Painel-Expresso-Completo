# NevesGo — Design System
### Guia de referência para implementação nativa em **Kotlin + Jetpack Compose + Material Design 3**

> Este documento foi gerado a partir da análise das 24 telas exportadas do Google Stitch para o app NevesGo (aplicativo para entregadores/motoboys autônomos). Cada token de cor, tipografia, espaçamento e raio abaixo foi **extraído e validado diretamente do código Tailwind real** gerado em cada tela (`code.html`), não estimado visualmente a partir dos prints. Onde uma decisão de design precisou ser tomada (paleta, nome, dark mode), isso está sinalizado explicitamente.

---

## Decisões-base deste documento

| Decisão | Valor | Origem |
|---|---|---|
| Nome do app | **NevesGo** | Assumido a partir do nome do arquivo enviado. As telas do Stitch traziam 3 nomes-placeholder inconsistentes (FlashLogistics, Velocity Logistics, RapidCourier) — todos devem ser ignorados/substituídos. |
| Stack de implementação | **Kotlin + Jetpack Compose + Material Design 3** | Definido pelo usuário. |
| Paleta | **Única em todo o app** (preto/vermelho) | Definido pelo usuário. A tela `dashboard_entregador_premium_simplificado` usava uma paleta alternativa (azul-marinho `#0F172A` / verde `#006E2F`) — **essa variação foi descontinuada**. Ver nota na seção 8.13 sobre como sinalizar "Premium" sem quebrar a paleta única. |
| Dark mode | Formalizado neste documento | O Tailwind config já trazia `darkMode: "class"` e 9 das 24 telas tinham variantes `dark:` parciais. Os valores exatos de superfície no dark mode foram **aproximados** a partir dos tokens "Fixed" já existentes — ver nota na seção 2.2. |
| Escopo | 24 telas catalogadas na seção 9.2 | Não há telas de login/onboarding/splash no pacote recebido. Os componentes deste documento (inputs, botões, OTP) servem para esse fluxo também, caso precise ser desenhado depois. |

---

## 1. Visão Geral do Produto & Princípios de Marca

**O que é**: app para entregadores/motoboys autônomos gerenciarem escalas fixas (turnos em estabelecimentos), entregas avulsas multi-pedido, carteira/saque de ganhos, documentação obrigatória (CNH, CRLV) e suporte — em português (pt-BR), moeda R$.

**Personalidade de marca**: *"Corporate Modern com viés funcional"* — a estética de uma central logística de alta performance, não de um app de consumo casual. Isso se traduz em:

- **Alto contraste, zero ambiguidade**: preto e branco fazem o trabalho estrutural pesado; a cor só aparece para comunicar dinheiro, urgência ou ação.
- **Precisão de dados**: valores monetários e códigos usam uma fonte separada (monoespaçada) — o app trata dinheiro e identificadores como informação crítica, não decorativa.
- **Confiança operacional**: cada tela de risco (desistir de escala, confirmar entrega, solicitar saque) usa avisos explícitos com consequência nomeada, nunca um genérico "tem certeza?".
- **Feita para uso em movimento**: alvos de toque grandes (56dp), uma mão, alto contraste para leitura sob luz solar direta.

**Público-alvo**: entregadores profissionais (moto/bike), muitas vezes usando o app enquanto dirigem ou aguardam em pontos de coleta — não um público de "compras por lazer".

---

## 2. Tokens de Cor

O sistema de cor segue os *color roles* do Material Design 3 (par `cor` / `on-cor`, mais os pares `-container`). Isso já era a base usada pelo Stitch — o trabalho aqui foi **validar contra o código real, remover a inconsistência do dashboard Premium e formalizar o dark mode**.

### 2.1 Paleta Light (padrão em 23 das 24 telas — agora em 24/24)

| Token M3 | Hex | Uso observado nas telas |
|---|---|---|
| `primary` | `#000000` | Texto de destaque, ícones estruturais, fundo de cards escuros (ex. card "Veículo Atual") |
| `onPrimary` | `#FFFFFF` | Texto/ícone sobre `primary` |
| `primaryContainer` | `#1B1B1B` | Superfícies escuras secundárias (banner de aviso no bottom sheet de desistência) |
| `onPrimaryContainer` | `#848484` | Texto de baixo destaque sobre `primaryContainer` ⚠️ contraste próximo do limite — validar em texto pequeno |
| `inversePrimary` | `#C6C6C6` | Estado ativo de ícone sobre superfícies invertidas |
| **`secondary`** | **`#B71519`** | **Cor de ação**: todo CTA primário, "Aceitar", tab ativa, valores de ganho, alertas de urgência |
| `onSecondary` | `#FFFFFF` | Texto sobre botões vermelhos |
| `secondaryContainer` | `#DB332F` | Chip "Confirmado", destaque "Destino Atual" |
| `onSecondaryContainer` | `#FFFBFF` | Texto sobre `secondaryContainer` |
| `tertiary` | `#000000` | Reservado (baixo uso direto) |
| `onTertiary` | `#FFFFFF` | — |
| `tertiaryContainer` | `#2A1700` | Fundo escuro de badges de alerta pontuais |
| `onTertiaryContainer` | `#B87500` | Texto âmbar sobre `tertiaryContainer` |
| `error` | `#BA1A1A` | Erros de formulário, validação |
| `onError` | `#FFFFFF` | — |
| `errorContainer` | `#FFDAD6` | Fundo de avisos de risco (ex. "cancelamento impacta seu Score") |
| `onErrorContainer` | `#93000A` | Texto sobre `errorContainer` |
| `background` / `surface` | `#F7F9FB` | Fundo padrão de tela |
| `onBackground` / `onSurface` | `#191C1E` | Texto padrão |
| `surfaceVariant` | `#E0E3E5` | — |
| `onSurfaceVariant` | `#4C4546` | Texto secundário, labels, placeholders |
| `outline` | `#7E7576` | Bordas de ícones ativos |
| `outlineVariant` | `#CFC4C5` | Borda padrão de inputs e divisores |
| `surfaceTint` | `#5E5E5E` | — |
| `inverseSurface` | `#2D3133` | Base do dark mode (ver 2.2) |
| `inverseOnSurface` | `#EFF1F3` | Base do dark mode (ver 2.2) |
| `surfaceDim` | `#D8DADC` | — |
| `surfaceBright` | `#F7F9FB` | — |
| `surfaceContainerLowest` | `#FFFFFF` | Cards elevados (branco puro) |
| `surfaceContainerLow` | `#F2F4F6` | Fundo de inputs habilitados |
| `surfaceContainer` | `#ECEEF0` | Fundo de inputs desabilitados, seções neutras |
| `surfaceContainerHigh` | `#E6E8EA` | Chips neutros ("Agendado") |
| `surfaceContainerHighest` | `#E0E3E5` | Camada de maior elevação |
| `primaryFixed` / `Dim` | `#E2E2E2` / `#C6C6C6` | Base para derivação do dark mode |
| `onPrimaryFixed` / `Variant` | `#1B1B1B` / `#474747` | Base para derivação do dark mode |
| `secondaryFixed` / `Dim` | `#FFDAD6` / `#FFB4AB` | Base para derivação do dark mode |
| `onSecondaryFixed` / `Variant` | `#410002` / `#93000C` | Base para derivação do dark mode |
| `tertiaryFixed` / `Dim` | `#FFDDB8` / `#FFB95F` | Base para derivação do dark mode |
| `onTertiaryFixed` / `Variant` | `#2A1700` / `#653E00` | Base para derivação do dark mode |

**Cor semântica extra (fora do M3 base, mas usada de fato no código em `saque_realizado`, `corrida_finalizada`, saldo positivo)**: as telas usam verde puro do Tailwind (`green-500`/`green-600`) sem um token formal. Formalizei isso como `success`:

| Token (extensão NevesGo) | Hex | Uso |
|---|---|---|
| `success` | `#16A34A` | Ícone/texto de confirmação (saque concluído, entrega finalizada) |
| `onSuccess` | `#FFFFFF` | — |
| `successContainer` | `#DCFCE7` | Fundo do círculo de check em telas de sucesso |
| `onSuccessContainer` | `#14532D` | — |

### 2.2 Paleta Dark (formalizada por este documento)

O Stitch **não exportou uma rampa tonal completa** para o dark mode — apenas classes `dark:` pontuais em 9 telas. Os valores abaixo foram **derivados matematicamente dos tokens "Fixed" já existentes** (essa é literalmente a função dos tokens Fixed/FixedDim no M3: permitir reconstruir o par claro/escuro a partir de uma única exportação). Os tons de `primary`/`secondary`/`tertiary` abaixo têm alta confiança; os tons de superfície (`surfaceContainer*`, `outline`) são uma **aproximação por overlay** e valem uma passada fina no [Material Theme Builder](https://m3.material.io/theme-builder) antes de produção.

| Token M3 | Hex (dark) | Derivação |
|---|---|---|
| `primary` | `#C6C6C6` | = `primaryFixedDim` |
| `onPrimary` | `#1B1B1B` | = `onPrimaryFixed` |
| `primaryContainer` | `#474747` | = `onPrimaryFixedVariant` |
| `onPrimaryContainer` | `#E2E2E2` | = `primaryFixed` |
| `secondary` | `#FFB4AB` | = `secondaryFixedDim` |
| `onSecondary` | `#410002` | = `onSecondaryFixed` |
| `secondaryContainer` | `#93000C` | = `onSecondaryFixedVariant` |
| `onSecondaryContainer` | `#FFDAD6` | = `secondaryFixed` |
| `tertiary` | `#FFB95F` | = `tertiaryFixedDim` |
| `onTertiary` | `#2A1700` | = `onTertiaryFixed` |
| `tertiaryContainer` | `#653E00` | = `onTertiaryFixedVariant` |
| `onTertiaryContainer` | `#FFDDB8` | = `tertiaryFixed` |
| `background` / `surface` | `#2D3133` | = `inverseSurface` |
| `onBackground` / `onSurface` | `#EFF1F3` | = `inverseOnSurface` |
| `error` | `#FFB4AB` | Paleta de erro padrão M3 (a paleta light já é a baseline default do Google) |
| `onError` | `#690005` | idem |
| `errorContainer` | `#93000A` | idem |
| `onErrorContainer` | `#FFDAD6` | idem |
| `outline` | `#999FA4` | ⚠️ Aproximado |
| `outlineVariant` | `#45474A` | ⚠️ Aproximado |
| `surfaceContainerLowest` | `#1C1E20` | ⚠️ Aproximado (overlay branco ~0% sobre `#2D3133`) |
| `surfaceContainerLow` | `#34373A` | ⚠️ Aproximado (overlay ~4%) |
| `surfaceContainer` | `#393C3F` | ⚠️ Aproximado (overlay ~8%) |
| `surfaceContainerHigh` | `#444749` | ⚠️ Aproximado (overlay ~11%) |
| `surfaceContainerHighest` | `#4F5254` | ⚠️ Aproximado (overlay ~15%) |

### 2.3 Color.kt

```kotlin
package com.nevesgo.app.ui.theme

import androidx.compose.ui.graphics.Color

// ===== Light =====
val Primary = Color(0xFF000000)
val OnPrimary = Color(0xFFFFFFFF)
val PrimaryContainer = Color(0xFF1B1B1B)
val OnPrimaryContainer = Color(0xFF848484)
val InversePrimary = Color(0xFFC6C6C6)

val Secondary = Color(0xFFB71519)
val OnSecondary = Color(0xFFFFFFFF)
val SecondaryContainer = Color(0xFFDB332F)
val OnSecondaryContainer = Color(0xFFFFFBFF)

val Tertiary = Color(0xFF000000)
val OnTertiary = Color(0xFFFFFFFF)
val TertiaryContainer = Color(0xFF2A1700)
val OnTertiaryContainer = Color(0xFFB87500)

val Error = Color(0xFFBA1A1A)
val OnError = Color(0xFFFFFFFF)
val ErrorContainer = Color(0xFFFFDAD6)
val OnErrorContainer = Color(0xFF93000A)

val Background = Color(0xFFF7F9FB)
val OnBackground = Color(0xFF191C1E)
val Surface = Color(0xFFF7F9FB)
val OnSurface = Color(0xFF191C1E)
val SurfaceVariant = Color(0xFFE0E3E5)
val OnSurfaceVariant = Color(0xFF4C4546)

val Outline = Color(0xFF7E7576)
val OutlineVariant = Color(0xFFCFC4C5)
val SurfaceTint = Color(0xFF5E5E5E)

val InverseSurface = Color(0xFF2D3133)
val InverseOnSurface = Color(0xFFEFF1F3)

val SurfaceDim = Color(0xFFD8DADC)
val SurfaceBright = Color(0xFFF7F9FB)
val SurfaceContainerLowest = Color(0xFFFFFFFF)
val SurfaceContainerLow = Color(0xFFF2F4F6)
val SurfaceContainer = Color(0xFFECEEF0)
val SurfaceContainerHigh = Color(0xFFE6E8EA)
val SurfaceContainerHighest = Color(0xFFE0E3E5)

val PrimaryFixed = Color(0xFFE2E2E2)
val PrimaryFixedDim = Color(0xFFC6C6C6)
val OnPrimaryFixed = Color(0xFF1B1B1B)
val OnPrimaryFixedVariant = Color(0xFF474747)

val SecondaryFixed = Color(0xFFFFDAD6)
val SecondaryFixedDim = Color(0xFFFFB4AB)
val OnSecondaryFixed = Color(0xFF410002)
val OnSecondaryFixedVariant = Color(0xFF93000C)

val TertiaryFixed = Color(0xFFFFDDB8)
val TertiaryFixedDim = Color(0xFFFFB95F)
val OnTertiaryFixed = Color(0xFF2A1700)
val OnTertiaryFixedVariant = Color(0xFF653E00)

// Extensão semântica — não faz parte do M3 base, formalizada a partir do uso real (green-500/600)
val Success = Color(0xFF16A34A)
val OnSuccess = Color(0xFFFFFFFF)
val SuccessContainer = Color(0xFFDCFCE7)
val OnSuccessContainer = Color(0xFF14532D)

// ===== Dark (derivado dos tokens Fixed — ver seção 2.2 do design system) =====
val PrimaryDark = PrimaryFixedDim
val OnPrimaryDark = OnPrimaryFixed
val PrimaryContainerDark = OnPrimaryFixedVariant
val OnPrimaryContainerDark = PrimaryFixed

val SecondaryDark = SecondaryFixedDim
val OnSecondaryDark = OnSecondaryFixed
val SecondaryContainerDark = OnSecondaryFixedVariant
val OnSecondaryContainerDark = SecondaryFixed

val TertiaryDark = TertiaryFixedDim
val OnTertiaryDark = OnTertiaryFixed
val TertiaryContainerDark = OnTertiaryFixedVariant
val OnTertiaryContainerDark = TertiaryFixed

val BackgroundDark = Color(0xFF2D3133)
val OnBackgroundDark = Color(0xFFEFF1F3)
val SurfaceDark = Color(0xFF2D3133)
val OnSurfaceDark = Color(0xFFEFF1F3)

val ErrorDark = Color(0xFFFFB4AB)
val OnErrorDark = Color(0xFF690005)
val ErrorContainerDark = Color(0xFF93000A)
val OnErrorContainerDark = Color(0xFFFFDAD6)

// ⚠️ Aproximado — ajuste fino recomendado via Material Theme Builder (seed #2D3133)
val OutlineDark = Color(0xFF999FA4)
val OutlineVariantDark = Color(0xFF45474A)
val OnSurfaceVariantDark = Color(0xFFC9C5C4)
val SurfaceContainerLowestDark = Color(0xFF1C1E20)
val SurfaceContainerLowDark = Color(0xFF34373A)
val SurfaceContainerDark = Color(0xFF393C3F)
val SurfaceContainerHighDark = Color(0xFF444749)
val SurfaceContainerHighestDark = Color(0xFF4F5254)
```

### 2.4 Theme.kt

```kotlin
package com.nevesgo.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val NevesGoLightColors = lightColorScheme(
    primary = Primary, onPrimary = OnPrimary,
    primaryContainer = PrimaryContainer, onPrimaryContainer = OnPrimaryContainer,
    inversePrimary = InversePrimary,
    secondary = Secondary, onSecondary = OnSecondary,
    secondaryContainer = SecondaryContainer, onSecondaryContainer = OnSecondaryContainer,
    tertiary = Tertiary, onTertiary = OnTertiary,
    tertiaryContainer = TertiaryContainer, onTertiaryContainer = OnTertiaryContainer,
    background = Background, onBackground = OnBackground,
    surface = Surface, onSurface = OnSurface,
    surfaceVariant = SurfaceVariant, onSurfaceVariant = OnSurfaceVariant,
    surfaceTint = SurfaceTint,
    inverseSurface = InverseSurface, inverseOnSurface = InverseOnSurface,
    error = Error, onError = OnError,
    errorContainer = ErrorContainer, onErrorContainer = OnErrorContainer,
    outline = Outline, outlineVariant = OutlineVariant,
    surfaceBright = SurfaceBright, surfaceDim = SurfaceDim,
    surfaceContainer = SurfaceContainer,
    surfaceContainerHigh = SurfaceContainerHigh,
    surfaceContainerHighest = SurfaceContainerHighest,
    surfaceContainerLow = SurfaceContainerLow,
    surfaceContainerLowest = SurfaceContainerLowest,
    primaryFixed = PrimaryFixed, primaryFixedDim = PrimaryFixedDim,
    onPrimaryFixed = OnPrimaryFixed, onPrimaryFixedVariant = OnPrimaryFixedVariant,
    secondaryFixed = SecondaryFixed, secondaryFixedDim = SecondaryFixedDim,
    onSecondaryFixed = OnSecondaryFixed, onSecondaryFixedVariant = OnSecondaryFixedVariant,
    tertiaryFixed = TertiaryFixed, tertiaryFixedDim = TertiaryFixedDim,
    onTertiaryFixed = OnTertiaryFixed, onTertiaryFixedVariant = OnTertiaryFixedVariant,
)

private val NevesGoDarkColors = darkColorScheme(
    primary = PrimaryDark, onPrimary = OnPrimaryDark,
    primaryContainer = PrimaryContainerDark, onPrimaryContainer = OnPrimaryContainerDark,
    inversePrimary = Primary,
    secondary = SecondaryDark, onSecondary = OnSecondaryDark,
    secondaryContainer = SecondaryContainerDark, onSecondaryContainer = OnSecondaryContainerDark,
    tertiary = TertiaryDark, onTertiary = OnTertiaryDark,
    tertiaryContainer = TertiaryContainerDark, onTertiaryContainer = OnTertiaryContainerDark,
    background = BackgroundDark, onBackground = OnBackgroundDark,
    surface = SurfaceDark, onSurface = OnSurfaceDark,
    onSurfaceVariant = OnSurfaceVariantDark,
    error = ErrorDark, onError = OnErrorDark,
    errorContainer = ErrorContainerDark, onErrorContainer = OnErrorContainerDark,
    outline = OutlineDark, outlineVariant = OutlineVariantDark,
    surfaceContainer = SurfaceContainerDark,
    surfaceContainerHigh = SurfaceContainerHighDark,
    surfaceContainerHighest = SurfaceContainerHighestDark,
    surfaceContainerLow = SurfaceContainerLowDark,
    surfaceContainerLowest = SurfaceContainerLowestDark,
)

@Composable
fun NevesGoTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) NevesGoDarkColors else NevesGoLightColors,
        typography = NevesGoTypography,
        shapes = NevesGoShapes,
        content = content
    )
}
```

---

## 3. Tipografia

Duas famílias, com papéis bem separados — isso é uma decisão de marca, não acidente: **Inter** conduz toda a interface; **Geist Mono** aparece *exclusivamente* onde a legibilidade de dígitos importa (confirmado no código: valores como `+ R$ 24,90` e `- R$ 450,00` na Carteira usam a classe `font-data-mono`).

> **Nota de correção**: o `code.html` original importava a fonte **"Geist"** (variante sans-serif) para o papel de "mono", o que não cumpre o próprio objetivo declarado no `DESIGN.md` do Stitch ("evitar confusão de caracteres em códigos"). Troquei para **Geist Mono** (a variante monoespaçada real da mesma família — confirmada disponível no Google Fonts) para cumprir esse objetivo de fato.

### 3.1 Escala

| Estilo (nome Stitch) | Slot Compose M3 | Fonte / Peso / Tamanho / Altura / Tracking | Uso |
|---|---|---|---|
| `headline-lg` | `headlineLarge` | Inter / 700 / 24sp / 32sp / -0.02em | Saldo, título de sucesso ("Sucesso!") |
| `headline-md` | `headlineMedium`, `headlineSmall` | Inter / 600 / 20sp / 28sp / -0.01em | Nome do card, título de tela, texto de botão CTA |
| `body-lg` | `bodyLarge` | Inter / 500 / 18sp / 26sp | Descrição de atividades, texto de leitura confortável |
| `body-md` | `bodyMedium` | Inter / 400 / 16sp / 24sp | Texto padrão, valor de input |
| `label-lg` | `labelLarge` | Inter / 600 / 14sp / 20sp / +0.01em | Labels de campo, texto de chip grande |
| `label-sm` | `labelSmall`, `labelMedium` | Inter / 500 / 12sp / 16sp / +0.02em | Timestamps, tabs, legendas, chips pequenos |
| `data-mono` *(custom, fora do M3)* | — | **Geist Mono** / 600 / 16sp / 24sp | Valores monetários, código de pedido (#F8921), OTP |

### 3.2 Type.kt

```kotlin
package com.nevesgo.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

// Requer o array de certificados gerado pelo assistente "Downloadable Fonts"
// do Android Studio (File > New > Resource > Font) — ele cria
// R.array.com_google_android_gms_fonts_certs automaticamente.
private val provider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = R.array.com_google_android_gms_fonts_certs
)

val InterFontFamily = FontFamily(
    Font(GoogleFont("Inter"), provider, FontWeight.Normal),
    Font(GoogleFont("Inter"), provider, FontWeight.Medium),
    Font(GoogleFont("Inter"), provider, FontWeight.SemiBold),
    Font(GoogleFont("Inter"), provider, FontWeight.Bold),
)

val GeistMonoFontFamily = FontFamily(
    Font(GoogleFont("Geist Mono"), provider, FontWeight.SemiBold),
)

// Estilo customizado — não é um slot padrão do M3, usar diretamente:
// Text("R$ 1.248,50", style = DataMono)
val DataMono = TextStyle(
    fontFamily = GeistMonoFontFamily,
    fontWeight = FontWeight.SemiBold,
    fontSize = 16.sp,
    lineHeight = 24.sp,
)

val NevesGoTypography = Typography(
    headlineLarge = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.Bold,
        fontSize = 24.sp, lineHeight = 32.sp, letterSpacing = (-0.02).em,
    ),
    headlineMedium = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.SemiBold,
        fontSize = 20.sp, lineHeight = 28.sp, letterSpacing = (-0.01).em,
    ),
    headlineSmall = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.SemiBold,
        fontSize = 20.sp, lineHeight = 28.sp, letterSpacing = (-0.01).em,
    ),
    bodyLarge = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.Medium,
        fontSize = 18.sp, lineHeight = 26.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.Normal,
        fontSize = 16.sp, lineHeight = 24.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp, lineHeight = 20.sp, letterSpacing = 0.01.em,
    ),
    labelMedium = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.Medium,
        fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.02.em,
    ),
    labelSmall = TextStyle(
        fontFamily = InterFontFamily, fontWeight = FontWeight.Medium,
        fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.02.em,
    ),
)
```

---

## 4. Formas & Raios

```kotlin
package com.nevesgo.app.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val NevesGoShapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),   // badges pequenos
    small = RoundedCornerShape(8.dp),        // inputs, botões-padrão
    medium = RoundedCornerShape(12.dp),      // cards, CTA principal ("Aceitar Escala")
    large = RoundedCornerShape(16.dp),       // cards de destaque, bottom sheets
    extraLarge = RoundedCornerShape(24.dp),  // modais grandes
)

// Fora do objeto Shapes padrão do M3 — chips e status usam pill 100%
val PillShape = RoundedCornerShape(percent = 50)
```

---

## 5. Espaçamento & Grid

Grid base de 4dp. `gutter` (margem lateral de tela) e `stackGap` (espaço entre elementos empilhados) confirmados no código (`px-gutter`, paddings recorrentes de 16/12dp entre cards).

```kotlin
package com.nevesgo.app.ui.theme

import androidx.compose.ui.unit.dp

object NevesGoSpacing {
    val base = 4.dp
    val xs = 8.dp
    val sm = 12.dp          // gap entre elementos empilhados dentro de um card
    val md = 16.dp          // gutter — margem lateral padrão de tela
    val lg = 24.dp
    val xl = 32.dp

    val touchTargetMin = 48.dp   // mínimo de acessibilidade
    val ctaHeight = 56.dp        // altura real de botões primários e inputs (acima do mínimo)
}
```

---

## 6. Elevação & Sombra

O Stitch usa camadas de `surface-container-*` (elevação tonal) combinadas com sombra leve pontual em componentes flutuantes (CTA fixo com `shadow-lg` + `backdrop-blur`, bottom nav com `shadow-lg`).

| Nível | Token de cor (light) | Uso | `tonalElevation` sugerida |
|---|---|---|---|
| 0 — Base | `surface` | Fundo de tela | 0dp |
| 1 — Card padrão | `surfaceContainerLowest` (branco) + sombra 2dp | Cards de escala/entrega | 1dp |
| 2 — Destaque neutro | `surfaceContainerHigh` | Chips neutros, seções de resumo | 3dp |
| 3 — Flutuante | `surface` + `shadowElevation` 8dp + blur de fundo | CTA fixo no rodapé, bottom nav | — (usar `shadowElevation`, não tonal) |
| 4 — Modal | `surfaceContainerHighest` | Bottom sheets | 6dp |

Regra prática: **prefira `surfaceContainer*` a `tonalElevation` alta** para cards estáticos (é o padrão M3 1.3+ e é como o Stitch já constrói a hierarquia visual); reserve sombra real (`shadowElevation`) para elementos que flutuam sobre conteúdo (CTA fixo, FAB, bottom nav, bottom sheet).

---

## 7. Iconografia

Ícones no Stitch usam a fonte **Material Symbols Outlined** (web). Em Compose nativo, o equivalente é a biblioteca `material-icons-extended`. Regra de estado: **ícone outlined quando inativo, preenchido (`Filled`) quando ativo/selecionado** — confirmado no código da bottom nav (`font-variation-settings: 'FILL' 1` na aba ativa).

| Ícone (Stitch) | Compose (`material-icons-extended`) | Uso |
|---|---|---|
| `home` | `Icons.Outlined.Home` / `Icons.Filled.Home` | Tab Início |
| `local_shipping` | `Icons.Outlined.LocalShipping` / `Filled` | Tab Entregas |
| `calendar_month` | `Icons.Outlined.CalendarMonth` / `Filled` | Tab Escala |
| `person` | `Icons.Outlined.Person` / `Filled` | Tab Perfil |
| `check_circle` | `Icons.Outlined.CheckCircle` | Sucesso, documento aprovado |
| `arrow_back` | `Icons.AutoMirrored.Outlined.ArrowBack` | Voltar (topo) |
| `location_on` | `Icons.Outlined.LocationOn` | Endereços, pins de mapa |
| `chevron_right` | `Icons.AutoMirrored.Outlined.KeyboardArrowRight` | Itens de lista/menu |
| `account_balance_wallet` / `payments` | `Icons.Outlined.AccountBalanceWallet` / `Payments` | Carteira, ganhos |
| `schedule` / `timer` | `Icons.Outlined.Schedule` / `Timer` | Turnos, ETA |
| `notifications` | `Icons.Outlined.Notifications` | Sino no topo |
| `search` | `Icons.Outlined.Search` | Central de Ajuda |
| `warning` | `Icons.Outlined.WarningAmber` | Avisos de risco |
| `route` | `Icons.AutoMirrored.Outlined.Route` | "Ver Rota" |
| `my_location` | `Icons.Outlined.MyLocation` | FAB recentralizar mapa |
| `call` | `Icons.Outlined.Call` | Ligar pro cliente |
| `bookmark` | `Icons.Outlined.BookmarkBorder` | Salvar vaga |
| `support_agent` | `Icons.Outlined.SupportAgent` | Suporte |
| `security` / `lock` | `Icons.Outlined.Security` / `Lock` | Segurança e senha |
| `verified_user` | `Icons.Outlined.VerifiedUser` | Selo de verificação |
| `sync` / `refresh` | `Icons.Outlined.Sync` / `Refresh` | Atualizar dados |
| `help` | `Icons.AutoMirrored.Outlined.HelpOutline` | Ajuda |
| `bolt` | `Icons.Outlined.Bolt` | CTA "Aceitar Escala" |
| `logout` | `Icons.AutoMirrored.Outlined.Logout` | Sair da conta |
| `inventory_2` | `Icons.Outlined.Inventory2` | Volume do pacote |
| `store` | `Icons.Outlined.Store` | Estabelecimento (coleta) |
| `electric_moped` | ⚠️ verificar disponibilidade no set instalado — se ausente, usar `Icons.Outlined.TwoWheeler` como alternativa ou importar um asset vetorial próprio | Veículo do entregador |

Dependência: `implementation("androidx.compose.material:material-icons-extended:<versão do BOM>")`.

---

## 8. Biblioteca de Componentes

### 8.1 Botão Primário (CTA)
Full-width, **56dp de altura**, `secondary`/`onSecondary`, `shape.medium` (12dp), tipografia `headlineMedium`, ícone opcional à direita (ex. `bolt` em "Aceitar Escala"), `shadow` leve, feedback de toque `scale(0.98f)`.

```kotlin
@Composable
fun NevesGoPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().height(NevesGoSpacing.ctaHeight),
        shape = MaterialTheme.shapes.medium,
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.secondary,
            contentColor = MaterialTheme.colorScheme.onSecondary,
        ),
        elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp),
    ) {
        Text(text, style = MaterialTheme.typography.headlineMedium)
        icon?.let { Spacer(Modifier.width(8.dp)); Icon(it, contentDescription = null) }
    }
}
```

### 8.2 Botão Secundário / Outline
Mesma altura (56dp), fundo transparente, borda `outlineVariant` ou `secondary` conforme contexto, texto `onSurface`. Usado para a ação "segura" em decisões binárias (ex. "Manter Escala").

### 8.3 Botão Destrutivo (Outline vermelho)
Borda e texto em `error`, fundo transparente. Usado para "Confirmar Desistência" — **sempre a opção secundária/menos proeminente na tela**, nunca a ação padrão.

### 8.4 Text Field (Input)
**56dp de altura**, `shape.small` (8dp), fundo `surfaceContainerLow`, borda `outlineVariant`. Foco: borda + ring `secondary` (1dp). Desabilitado: fundo `surfaceContainer`, texto `onSurfaceVariant`, cursor bloqueado (ex. campo de CPF mascarado).

### 8.5 Card (Escala / Entrega)
Fundo `surfaceContainerLowest`, `shape.large` (16dp), sombra 2dp, padding 16dp. Estrutura: ícone do estabelecimento + nome + chip de status (canto superior direito) → divisor → metadados em `labelSmall` (turno, distância, tempo) → valor de destaque em `headlineMedium` na cor `secondary` quando é ganho.

### 8.6 Status Chip / Badge
Pill (`PillShape`), padding 12dp horizontal / 4dp vertical, `labelSmall`. Paleta por contexto:

| Tom | Fundo | Texto | Exemplos observados |
|---|---|---|---|
| Success | `successContainer` | `onSuccessContainer` | "Concluído", "Aprovado" |
| Ativo/Ação | `secondaryContainer` | `onSecondaryContainer` | "Confirmado", "Entregando" |
| Neutro | `surfaceContainerHigh` | `onSurfaceVariant` | "Agendado", "Em análise" |
| Warning | `tertiaryFixed` | `onTertiaryFixed` | "Atenção" (documento a vencer) |
| Danger | `errorContainer` | `onErrorContainer` | Avisos de cancelamento |

```kotlin
enum class StatusTone { Success, Active, Warning, Neutral, Danger }

@Composable
fun StatusChip(text: String, tone: StatusTone, modifier: Modifier = Modifier) {
    val (bg, fg) = when (tone) {
        StatusTone.Success -> SuccessContainer to OnSuccessContainer
        StatusTone.Active -> MaterialTheme.colorScheme.secondaryContainer to MaterialTheme.colorScheme.onSecondaryContainer
        StatusTone.Warning -> TertiaryFixed to OnTertiaryFixed
        StatusTone.Neutral -> MaterialTheme.colorScheme.surfaceContainerHigh to MaterialTheme.colorScheme.onSurfaceVariant
        StatusTone.Danger -> MaterialTheme.colorScheme.errorContainer to MaterialTheme.colorScheme.onErrorContainer
    }
    Surface(color = bg, contentColor = fg, shape = PillShape, modifier = modifier) {
        Text(text, style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp))
    }
}
```

### 8.7 Bottom Navigation Bar
4 itens fixos: **Início · Entregas · Escala · Perfil**. Altura ~80dp (incl. safe area), fundo `surface`, borda superior `outlineVariant`, sombra para cima. Item ativo: ícone `Filled`, fundo pill `secondaryContainer` atrás do ícone+label, texto `onSecondaryContainer`. Item inativo: ícone `Outlined`, texto `onSurfaceVariant`. Toque: `scale(0.9f)`.

> **Carteira não é uma tab** — é acessada a partir do dashboard (Início) ou de um atalho, não faz parte da navegação persistente.

### 8.8 Top App Bar
Seta de voltar à esquerda, título em `headlineMedium` (centralizado ou alinhado à esquerda conforme tela), ações à direita (sino de notificação quase onipresente; busca só na Central de Ajuda; avatar em telas de perfil/segurança).

### 8.9 Bottom Sheet de Confirmação Destrutiva
Ícone de aviso em círculo (`errorContainer` ou `tertiaryFixed`), título direto ("Tem certeza que deseja desistir desta escala?"), texto de consequência específica dentro de um box `errorContainer`/borda `error`, resumo do impacto (valor, local, data). **Ordem dos botões**: ação seguro/positiva primeiro e mais proeminente (`NevesGoPrimaryButton`), ação destrutiva depois e em outline vermelho — esse padrão de "default seguro" deve ser preservado em toda confirmação de risco do app.

### 8.10 OTP Input
4 caixas quadradas (~56dp), `surfaceContainerLow`, borda `outlineVariant`; foco = borda `secondary`. Texto em `DataMono` ou `headlineMedium` centralizado.

### 8.11 Chat Bubble (Suporte)
Bolha do usuário: fundo `primary` (preto), texto `onPrimary`, alinhada à direita. Bolha do atendente: fundo `surfaceContainerHigh`, texto `onSurface`, alinhada à esquerda, com avatar circular. Timestamp em `labelSmall` cinza abaixo de cada bolha. Campo de mensagem fixo no rodapé + botão de enviar circular preto.

### 8.12 Switch / Toggle
Usado em "Online e Disponível" e "Biometria". **Estado ativo usa `Success` (verde), não `secondary`** — é uma convenção deliberada: vermelho = ação/urgência, verde = estado positivo ligado. Mantenha essa distinção; não migre os toggles para vermelho.

### 8.13 Badge/Selo "Premium" (sem quebrar a paleta única)
Como a decisão foi manter uma única paleta em todo o app, sinalize o nível Premium **sem cor estrutural própria**: um selo pequeno usando `tertiaryFixed`/`onTertiaryFixed` (o âmbar já existente na paleta, hoje reservado a alertas) ao lado do nome do usuário, ou um ícone de estrela/diamante preenchido em `secondary`. Evite recriar o azul-marinho/verde do protótipo original em qualquer tela.

### 8.14 FAB (sobre mapa)
Circular, 56dp, fundo `primary` (preto), ícone branco. Usado para recentralizar localização e alternar camadas do mapa.

### 8.15 Empty / Waiting State
Ícone ou ilustração simples + `headlineMedium` curto + `bodyMedium` de apoio + CTA opcional. Ex.: "Aguardando Coleta" com contagem de pedidos em espera.

### 8.16 Tela de Sucesso / Confirmação
Ícone circular grande de check (`successContainer` de fundo), `headlineLarge` ("Sucesso!"), `bodyMedium` de apoio, card-resumo, CTA primário de continuação + ação secundária em texto (ex. "Compartilhar Comprovante").

---

## 9. Navegação & Inventário de Telas

### 9.1 Arquitetura sugerida
`Scaffold` raiz com `bottomBar` condicional (visível nas 4 rotas-tab, oculto em telas empilhadas como Dados Pessoais ou Confirmar Código) + `NavHost` (Navigation Compose) com um grafo aninhado por tab. As 4 tabs abrem suas próprias pilhas; Carteira, Suporte, Central de Ajuda e as telas de Perfil são destinos empilhados a partir de Início/Perfil.

### 9.2 As 24 telas, por módulo

**Início**
- Dashboard do Entregador — status online/offline, pedidos próximos, ganhos do turno

**Escala** (turnos fixos)
- Disponíveis / Minhas Escalas (abas)
- Detalhes da Vaga (antes de aceitar)
- Detalhes da Escala Aceita (com mapa e cancelamento)
- Confirmar Desistência da Escala (bottom sheet)

**Entregas** (sob demanda)
- Entregas em Espera (fila)
- Iniciar Entrega Multi-Pedidos
- Confirmar Código de Entrega (OTP)
- Finalizar Entrega Multi-Pedidos
- Entrega Realizada — Próximo Passo
- Corrida Finalizada
- Minhas Entregas — Em Curso / Em Espera / Agendadas (abas)
- Detalhes do Agendamento

**Carteira**
- Carteira (saldo, filtro de período, transações)
- Solicitar Saque
- Saque Realizado

**Perfil**
- Perfil (hub)
- Dados Pessoais
- Segurança e Senha
- Histórico de Documentos

**Suporte**
- Central de Ajuda
- Suporte em Tempo Real (chat)

> Não incluído no pacote: login, cadastro, splash/onboarding. Os componentes das seções 8.4 (input) e 8.10 (OTP) já cobrem o necessário para desenhar esse fluxo depois, no mesmo sistema.

---

## 10. Estados & Microinterações

- **Toque**: `scale(0.90f)` em ícones de navegação, `scale(0.98f)` em botões — sempre com `animateFloatAsState` ou `Modifier.scale` + `Animatable`, nunca instantâneo.
- **Loading de lista**: preferir *skeleton* (formas cinza pulsantes no formato do card) a um spinner central genérico.
- **Transição de tela**: padrão do Navigation Compose (slide horizontal); bottom sheets sobem com fade+slide.
- **Motion reduzida**: respeitar a preferência de sistema (verificar `Settings.Global.ANIMATOR_DURATION_SCALE` / usar `MotionScheme` do M3, que já se adapta).

---

## 11. Conteúdo & Tom de Voz

- pt-BR direto e operacional — o usuário está trabalhando, muitas vezes em movimento.
- Avisos de risco nomeiam a consequência exata (já visto no app: *"O cancelamento com menos de 2h de antecedência poderá impactar seu Score de Confiabilidade"*) — nunca um genérico "tem certeza?".
- Botões nomeiam a ação exata: "Confirmar Entrega", "Aceitar Escala" — evitar "OK"/"Enviar" genéricos.
- Empty states como convite à ação, não vazio sem saída.

---

## 12. Acessibilidade

- Alvo de toque mínimo 48dp — botões reais já usam 56dp, acima do mínimo.
- `contentDescription` obrigatório em todo `IconButton` sem texto visível (FAB do mapa, ícone de enviar no chat).
- ⚠️ Validar contraste de `onPrimaryContainer` (`#848484`) sobre `primaryContainer` (`#1B1B1B`) com uma ferramenta de contraste antes de usar em texto pequeno — pode não atingir AA para texto normal, mesmo sendo aceitável para ícones/texto grande.
- Tipografia em `sp` (já respeitado no `Type.kt`) para escalar com a preferência de fonte do sistema.
- Compatibilidade com TalkBack: `Modifier.semantics` nos componentes customizados (chips, cards clicáveis).

---

## 13. Dependências Técnicas Recomendadas

```kotlin
// build.gradle.kts (module: app)
implementation("androidx.compose.material3:material3:<versão do BOM>")
implementation("androidx.compose.material:material-icons-extended")
implementation("androidx.compose.ui:ui-text-google-fonts") // Inter + Geist Mono via Google Fonts
implementation("androidx.navigation:navigation-compose:<versão>")
implementation("com.google.maps.android:maps-compose:<versão>") // mapas nas telas de escala/entrega
implementation("io.coil-kt:coil-compose:<versão>") // avatares e fotos de estabelecimento
```

---

## 14. Como Usar Este Documento com Seu Agente

1. Cole este arquivo inteiro (ou referencie como `docs/design-system.md` no repositório) como contexto do projeto antes de pedir qualquer tela.
2. Peça primeiro a montagem da **camada de tokens** (`Color.kt`, `Type.kt`, `Shape.kt`, `Dimens.kt`, `Theme.kt`) exatamente como especificado aqui — antes de gerar qualquer componente ou tela.
3. Depois, peça **uma tela por vez**, citando o nome exato da seção 9.2 e pedindo aderência aos componentes da seção 8. Evite pedir as 24 de uma vez — a qualidade cai e a aderência aos tokens também.
4. Ao final de cada tela, peça uma revisão explícita: *"confira se esta tela usa `MaterialTheme.colorScheme`/`typography` em vez de cores ou tamanhos hardcoded"*.
5. Reforce que **a paleta é única em todo o app** (seção 8.13 explica como sinalizar Premium sem cor própria) — esse é o ponto onde um agente tende a reintroduzir a inconsistência do protótipo original se não for lembrado.