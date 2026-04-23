# Modelo Operativo — Magma

## Arquitectura de Sostenibilidad

### Fase 1: MVP (actual)
- Backend Python puro desplegado en Hetzner VPS
- Frontend SvelteKit en Cloudflare Pages
- Base de datos PostgreSQL en Docker
- Autenticación vía Nostr (LNURL-auth)
- Costo mensual estimado: $15-25 USD

### Fase 2: Crecimiento (3-6 meses)
- Integración con LNbits para servicios avanzados
- NWC (Nostr Wallet Connect) para ejecución de pagos
- API de precios multicotizadora (CoinGecko + Yadio + Bitrefill)
- Notificaciones push para alertas de precio y comisiones

### Fase 3: Escala (6-12 meses)
- App móvil nativa (considerar Capacitor desde SvelteKit)
- Partnerships con comercios en El Salvador
- Módulo de microcréditos P2P sobre Lightning
- Dashboard para ONGs y organizaciones de remesas

## Modelo de Ingresos

| Fuente | Descripción | Margen |
|--------|-------------|--------|
| Comisión de routing | Fee mínimo por enrutamiento Lightning (opcional) | 0.1-0.3% |
| Premium features | Alertas avanzadas, reportes de impuestos, multi-wallet | $2.99/mes |
| API para terceros | Acceso a engine de comparación de remesas | Por volumen |
| Consultoría | Integración para empresas/comercios | Por proyecto |

## Equipo

| Rol | Responsable | Enfoque |
|-----|-------------|---------|
| Desarrollo Full-Stack | Wilmer Salazar | Backend Python, Frontend SvelteKit, integración Lightning |
| UI/UX & Frontend | Iván Elías | Componentes visuales, experiencia de usuario |
| Estrategia & Negocio | Katherine Galdámez | Análisis de impacto, modelo operativo, pitch |
| Estrategia & Documentación | Lisbeth Cabrera | Investigación de mercado, documentación, work log |

## Métricas de Éxito

1. **Técnicas**: Uptime >99%, latencia API <200ms, 0 pérdida de fondos
2. **Adopción**: 100 usuarios activos en primer trimestre
3. **Impacto**: Reducción medible en costos de remesa para usuarios piloto
4. **Educación**: Tasa de completación >40% en módulos de aprendizaje

## Riesgos y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Regulación adversa | Media | Enfoque no-custodial elimina requisitos de licencia financiera |
| Adopción lenta | Alta | Gamificación + onboarding guiado + wallet guides |
| Volatilidad BTC | Alta | Educación sobre DCA y horizonte largo, módulo Liquid para stablecoins |
| Competencia (Strike, Chivo) | Media | Diferenciación por educación y transparencia open-source |
