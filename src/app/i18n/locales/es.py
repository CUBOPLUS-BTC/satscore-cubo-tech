"""
Spanish (es) translations for Magma Bitcoin app.
Traducciones al español para todos los mensajes de la API y la interfaz.
"""

TRANSLATIONS: dict = {

    # -----------------------------------------------------------------------
    # Auth
    # -----------------------------------------------------------------------
    "auth.challenge.issued":        "Desafío emitido correctamente.",
    "auth.challenge.expired":       "El desafío ha caducado. Por favor solicite uno nuevo.",
    "auth.challenge.not_found":     "No se encontró ningún desafío para esta clave pública.",
    "auth.challenge.mismatch":      "El desafío no coincide. Autenticación fallida.",
    "auth.challenge.required":      "Se requiere una cadena de desafío.",
    "auth.pubkey.required":         "Se requiere una clave pública (pubkey).",
    "auth.pubkey.invalid":          "Formato de clave pública inválido. Se esperan 64 caracteres hexadecimales.",
    "auth.success":                 "Autenticación exitosa.",
    "auth.failure":                 "Autenticación fallida. Verifique sus credenciales.",
    "auth.session.created":         "Sesión creada. Ha iniciado sesión correctamente.",
    "auth.session.invalid":         "El token de sesión es inválido o ha caducado.",
    "auth.session.expired":         "Su sesión ha caducado. Por favor inicie sesión nuevamente.",
    "auth.session.revoked":         "Sesión revocada correctamente.",
    "auth.session.not_found":       "Sesión no encontrada.",
    "auth.rate_limited":            "Demasiados intentos de autenticación. Espere {wait_seconds} segundos.",
    "auth.nostr.event.required":    "Se requiere un evento Nostr firmado.",
    "auth.nostr.event.invalid":     "El evento Nostr firmado es inválido.",
    "auth.nostr.pubkey.mismatch":   "La clave pública del evento no coincide con la solicitada.",
    "auth.lnurl.challenge.invalid": "El desafío de autenticación LNURL es inválido.",
    "auth.lnurl.signature.invalid": "La verificación de firma LNURL falló.",
    "auth.permission.denied":       "No tiene permiso para realizar esta acción.",

    # -----------------------------------------------------------------------
    # Savings
    # -----------------------------------------------------------------------
    "savings.goal.set":             "Meta de ahorro actualizada correctamente.",
    "savings.goal.not_found":       "No hay meta de ahorro configurada. Configure una para comenzar.",
    "savings.goal.required":        "Se requiere una meta de ahorro para esta acción.",
    "savings.deposit.recorded":     "Depósito de {amount} registrado correctamente.",
    "savings.deposit.invalid_amount": "El monto del depósito debe ser un número positivo.",
    "savings.deposit.not_found":    "Registro de depósito no encontrado.",
    "savings.projection.generated": "Proyección de ahorro generada.",
    "savings.projection.no_data":   "Datos insuficientes para generar una proyección. Realice al menos un depósito.",
    "savings.monthly_target":       "Meta mensual de ahorro",
    "savings.total_saved":          "Total ahorrado",
    "savings.total_btc":            "Total de BTC acumulado",
    "savings.target_years":         "Años objetivo",
    "savings.on_track":             "¡Está en camino de alcanzar su meta!",
    "savings.behind_target":        "Actualmente está por debajo de su meta mensual.",
    "savings.ahead_target":         "Va adelantado respecto a su meta mensual de ahorro.",
    "savings.no_deposits":          "Aún no hay depósitos registrados. ¡Empiece a ahorrar hoy!",

    # -----------------------------------------------------------------------
    # Remittance
    # -----------------------------------------------------------------------
    "remittance.calculation.success": "Cálculo de remesa completado.",
    "remittance.amount.invalid":    "Ingrese un monto de remesa válido.",
    "remittance.currency.invalid":  "Código de moneda inválido. Use un código ISO de 3 letras.",
    "remittance.rate.unavailable":  "El tipo de cambio no está disponible temporalmente. Intente de nuevo en breve.",
    "remittance.fee.breakdown":     "Desglose de comisiones",
    "remittance.recipient.receives": "El destinatario recibe",
    "remittance.sender.pays":       "El remitente paga",
    "remittance.via_bitcoin":       "Vía Bitcoin (instantáneo)",
    "remittance.via_traditional":   "Vía transferencia tradicional (3-5 días hábiles)",
    "remittance.savings_vs_traditional": "Ahorro vs. remesa tradicional",
    "remittance.no_data":           "Los datos de remesa no están disponibles en este momento.",

    # -----------------------------------------------------------------------
    # Pension
    # -----------------------------------------------------------------------
    "pension.projection.generated": "Proyección de pensión generada.",
    "pension.projection.no_data":   "Configure su meta de ahorro para generar una proyección de pensión.",
    "pension.age.required":         "La edad actual es necesaria para el cálculo de pensión.",
    "pension.age.invalid":          "La edad debe estar entre 18 y 80 años.",
    "pension.retirement_age":       "Edad de jubilación objetivo",
    "pension.years_to_retire":      "Años hasta la jubilación",
    "pension.projected_value":      "Valor proyectado del portafolio al jubilarse",
    "pension.monthly_income":       "Ingreso mensual estimado",
    "pension.inflation_adjusted":   "Valor ajustado por inflación",
    "pension.on_track":             "Va en camino hacia una jubilación cómoda.",
    "pension.underfunded":          "Su tasa de ahorro actual puede no alcanzar su meta de jubilación.",
    "pension.increase_savings":     "Considere aumentar su ahorro mensual para alcanzar su meta.",

    # -----------------------------------------------------------------------
    # Market
    # -----------------------------------------------------------------------
    "market.price.unavailable":     "Los datos de precio de Bitcoin no están disponibles temporalmente.",
    "market.price.fetched":         "Precio de mercado obtenido correctamente.",
    "market.fees.unavailable":      "Los datos de comisiones on-chain no están disponibles temporalmente.",
    "market.fees.fetched":          "Estimados de comisiones obtenidos correctamente.",
    "market.history.unavailable":   "El historial de precios no está disponible temporalmente.",
    "market.history.fetched":       "Historial de precios obtenido correctamente.",
    "market.loading":               "Cargando datos de mercado…",
    "market.last_updated":          "Última actualización",

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------
    "alerts.preferences.updated":  "Preferencias de alerta actualizadas.",
    "alerts.preferences.not_found": "No se encontraron preferencias de alerta. Se usarán los valores predeterminados.",
    "alerts.fee.triggered":         "Alerta de comisión Bitcoin: {direction} {level} sat/vB",
    "alerts.price.triggered":       "Alerta de precio Bitcoin: {direction} {price}",
    "alerts.fee.high":              "Las comisiones están ALTAS — actualmente {fee} sat/vB.",
    "alerts.fee.low":               "Las comisiones están BAJAS — actualmente {fee} sat/vB. ¡Buen momento para transaccionar!",
    "alerts.price.above":           "El precio de BTC superó {threshold}.",
    "alerts.price.below":           "El precio de BTC cayó por debajo de {threshold}.",
    "alerts.enabled":               "Las alertas están activadas.",
    "alerts.disabled":              "Las alertas están desactivadas.",

    # -----------------------------------------------------------------------
    # Achievements
    # -----------------------------------------------------------------------
    "achievements.earned":          "¡Logro desbloqueado: {name}!",
    "achievements.none":            "Aún no hay logros. ¡Empiece a ahorrar para ganar su primera medalla!",
    "achievements.all_fetched":     "Logros cargados.",

    # Achievement names
    "achievement.first_deposit.name":       "Primeros Pasos",
    "achievement.first_deposit.desc":       "Realizó su primer depósito de ahorro en Bitcoin.",
    "achievement.hodl_week.name":           "HODLer Semanal",
    "achievement.hodl_week.desc":           "Ahorró de manera consistente durante toda una semana.",
    "achievement.hodl_month.name":          "Apilador Mensual",
    "achievement.hodl_month.desc":          "Mantuvo su hábito de ahorro durante 30 días.",
    "achievement.goal_setter.name":         "Establecedor de Metas",
    "achievement.goal_setter.desc":         "Estableció su primera meta de ahorro.",
    "achievement.diamond_hands.name":       "Manos de Diamante",
    "achievement.diamond_hands.desc":       "Mantuvo su Bitcoin durante una caída del mercado del 10%.",
    "achievement.satoshi_100k.name":        "100K Satoshis",
    "achievement.satoshi_100k.desc":        "Acumuló 100.000 satoshis.",
    "achievement.satoshi_1m.name":          "1M Satoshis",
    "achievement.satoshi_1m.desc":          "Acumuló 1.000.000 de satoshis.",
    "achievement.satoshi_10m.name":         "10M Satoshis",
    "achievement.satoshi_10m.desc":         "Acumuló 10.000.000 de satoshis.",
    "achievement.on_track.name":            "En Camino",
    "achievement.on_track.desc":            "Se mantuvo en línea con su plan de ahorro durante un mes completo.",
    "achievement.nostr_auth.name":          "Nativo Nostr",
    "achievement.nostr_auth.desc":          "Se autenticó usando Nostr (NIP-07).",
    "achievement.streak_7.name":            "Racha de 7 Días",
    "achievement.streak_7.desc":            "Depositó todos los días durante 7 días consecutivos.",
    "achievement.streak_30.name":           "Racha de 30 Días",
    "achievement.streak_30.desc":           "Depositó todos los días durante 30 días consecutivos.",
    "achievement.early_adopter.name":       "Adoptante Temprano",
    "achievement.early_adopter.desc":       "Uno de los primeros 100 usuarios en Magma.",
    "achievement.big_saver.name":           "Gran Ahorrador",
    "achievement.big_saver.desc":           "Ahorró más de $500 en un solo mes.",
    "achievement.lightning_fast.name":      "Rayo Veloz",
    "achievement.lightning_fast.desc":      "Completó un pago en la Red Lightning.",

    # -----------------------------------------------------------------------
    # Notifications
    # -----------------------------------------------------------------------
    "notification.welcome.title":       "¡Bienvenido a Magma!",
    "notification.welcome.body":        "Comience su viaje de ahorro en Bitcoin hoy. Establezca una meta y haga su primer depósito.",
    "notification.deposit.title":       "Depósito Confirmado",
    "notification.deposit.body":        "Su depósito de {amount} ha sido registrado. Ha ahorrado {total} hasta ahora.",
    "notification.achievement.title":   "¡Logro Desbloqueado!",
    "notification.achievement.body":    'Ganó la medalla "{name}". ¡Siga apilando!',
    "notification.goal_reached.title":  "¡Meta de Ahorro Alcanzada!",
    "notification.goal_reached.body":   "¡Felicitaciones! Ha alcanzado su meta de ahorro de {goal}.",
    "notification.price_alert.title":   "Alerta de Precio Bitcoin",
    "notification.price_alert.body":    "BTC ahora está {direction} {threshold}. Precio actual: {price}.",
    "notification.fee_alert.title":     "Alerta de Comisiones",
    "notification.fee_alert.body":      "Las comisiones on-chain ahora están {level}: {fee} sat/vB.",
    "notification.streak.title":        "¡Racha de Ahorro!",
    "notification.streak.body":         "Lleva una racha de {days} días de ahorro. ¡No la rompa!",
    "notification.monthly_summary.title": "Resumen Mensual",
    "notification.monthly_summary.body":  "Este mes ahorró {amount}. Su total ahora es {total}.",

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------
    "export.generated":             "Exportación generada correctamente.",
    "export.format.pdf":            "Exportar PDF",
    "export.format.csv":            "Exportar CSV",
    "export.format.json":           "Exportar JSON",
    "export.no_data":               "No hay datos disponibles para exportar.",
    "export.savings_report":        "Reporte de Ahorros",
    "export.remittance_report":     "Reporte de Remesas",
    "export.pension_report":        "Reporte de Proyección de Pensión",
    "export.generated_by":          "Generado por Magma",
    "export.generated_on":          "Generado el",
    "export.confidential":          "Confidencial — solo para uso personal.",

    # -----------------------------------------------------------------------
    # Compliance / Admin
    # -----------------------------------------------------------------------
    "compliance.aml.low":           "Transacción de bajo riesgo.",
    "compliance.aml.medium":        "Riesgo medio — se requiere monitoreo.",
    "compliance.aml.high":          "Riesgo alto — se requiere revisión manual.",
    "compliance.aml.critical":      "Riesgo crítico — transacción bloqueada pendiente de revisión.",
    "compliance.ctr.required":      "Se requiere Reporte de Transacción de Divisas para ${amount}.",
    "compliance.sar.drafted":       "Reporte de Actividad Sospechosa redactado.",
    "compliance.alert.pending":     "Alerta de cumplimiento pendiente de revisión.",
    "compliance.alert.resolved":    "Alerta de cumplimiento resuelta.",
    "compliance.sanctioned_address": "Esta dirección está en una lista de sanciones. Transacción bloqueada.",
    "compliance.jurisdiction.sv":   "El Salvador (UAF)",
    "compliance.jurisdiction.us":   "Estados Unidos (FinCEN)",
    "compliance.jurisdiction.eu":   "Unión Europea (ABE)",

    "admin.access.denied":          "Acceso de administrador denegado.",
    "admin.access.not_configured":  "El acceso de administrador no está configurado en este servidor.",
    "admin.action.completed":       "Acción de administrador completada correctamente.",
    "admin.user.banned":            "El usuario {pubkey} ha sido bloqueado.",
    "admin.user.unbanned":          "El bloqueo del usuario {pubkey} ha sido levantado.",
    "admin.maintenance.completed":  "Mantenimiento completado en {elapsed_ms}ms.",
    "admin.config.updated":         "Clave de configuración '{key}' actualizada.",
    "admin.config.blocked":         "La clave de configuración '{key}' no puede modificarse en tiempo de ejecución.",

    # -----------------------------------------------------------------------
    # Errors
    # -----------------------------------------------------------------------
    "error.not_found":              "El recurso solicitado no fue encontrado.",
    "error.bad_request":            "La solicitud está malformada o le faltan campos requeridos.",
    "error.unauthorized":           "Se requiere autenticación.",
    "error.forbidden":              "No tiene permiso para acceder a este recurso.",
    "error.rate_limited":           "Demasiadas solicitudes. Por favor reduzca la frecuencia.",
    "error.internal":               "Ocurrió un error interno del servidor. Por favor intente de nuevo.",
    "error.database":               "Ocurrió un error en la base de datos. Contacte al soporte.",
    "error.validation.string":      "El campo '{field}' debe ser una cadena de texto.",
    "error.validation.number":      "El campo '{field}' debe ser un número.",
    "error.validation.range":       "El campo '{field}' debe estar entre {min} y {max}.",
    "error.validation.required":    "El campo '{field}' es obligatorio.",
    "error.validation.invalid":     "El campo '{field}' tiene un valor inválido.",
    "error.injection.detected":     "Se detectó entrada potencialmente maliciosa en el campo '{field}'.",
    "error.sanitization.failed":    "No se pudo sanitizar la entrada para el campo '{field}'.",
    "error.method.not_allowed":     "El método HTTP no está permitido para este endpoint.",
    "error.payload.too_large":      "El payload de la solicitud supera el tamaño máximo permitido.",
    "error.timeout":                "La solicitud agotó el tiempo de espera. Intente de nuevo.",
    "error.service.unavailable":    "Este servicio no está disponible temporalmente.",
    "error.bitcoin.address":        "Dirección Bitcoin inválida.",
    "error.lightning.invoice":      "Factura de Lightning Network inválida.",
    "error.nostr.pubkey":           "Clave pública Nostr inválida.",
    "error.amount.negative":        "El monto no puede ser negativo.",
    "error.amount.zero":            "El monto no puede ser cero.",
    "error.amount.too_large":       "El monto supera el valor máximo permitido.",
    "error.date.invalid":           "Formato de fecha inválido. Se espera AAAA-MM-DD.",
    "error.currency.invalid":       "Código de moneda inválido.",
    "error.json.invalid":           "Payload JSON inválido.",

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------
    "portfolio.summary":            "Resumen de Portafolio",
    "portfolio.current_value":      "Valor actual del portafolio",
    "portfolio.total_invested":     "Total invertido",
    "portfolio.unrealized_gain":    "Ganancia/pérdida no realizada",
    "portfolio.return_pct":         "Retorno total",
    "portfolio.btc_price_avg":      "Precio promedio de compra",
    "portfolio.holdings":           "Tenencias",
    "portfolio.no_data":            "No hay datos de portafolio disponibles. Realice su primer depósito para comenzar.",

    # -----------------------------------------------------------------------
    # General UI
    # -----------------------------------------------------------------------
    "general.loading":              "Cargando…",
    "general.saving":               "Guardando…",
    "general.success":              "¡Éxito!",
    "general.error":                "Ocurrió un error.",
    "general.cancel":               "Cancelar",
    "general.confirm":              "Confirmar",
    "general.save":                 "Guardar",
    "general.delete":               "Eliminar",
    "general.edit":                 "Editar",
    "general.view":                 "Ver",
    "general.back":                 "Atrás",
    "general.next":                 "Siguiente",
    "general.previous":             "Anterior",
    "general.close":                "Cerrar",
    "general.search":               "Buscar",
    "general.filter":               "Filtrar",
    "general.sort":                 "Ordenar",
    "general.export":               "Exportar",
    "general.import":               "Importar",
    "general.refresh":              "Actualizar",
    "general.yes":                  "Sí",
    "general.no":                   "No",
    "general.none":                 "Ninguno",
    "general.all":                  "Todo",
    "general.today":                "Hoy",
    "general.yesterday":            "Ayer",
    "general.this_week":            "Esta semana",
    "general.this_month":           "Este mes",
    "general.days_ago":             "hace {n} días",
    "general.hours_ago":            "hace {n} horas",
    "general.minutes_ago":          "hace {n} minutos",
    "general.just_now":             "Justo ahora",
    "general.unknown":              "Desconocido",
    "general.n_a":                  "N/D",
}
