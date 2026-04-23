"""
English (en) translations for Magma Bitcoin app.
All API responses, error messages, achievement descriptions, and notification templates.
"""

TRANSLATIONS: dict = {

    # -----------------------------------------------------------------------
    # Auth
    # -----------------------------------------------------------------------
    "auth.challenge.issued":        "Challenge issued successfully.",
    "auth.challenge.expired":       "Challenge has expired. Please request a new one.",
    "auth.challenge.not_found":     "No challenge found for this public key.",
    "auth.challenge.mismatch":      "Challenge mismatch. Authentication failed.",
    "auth.challenge.required":      "A challenge string is required.",
    "auth.pubkey.required":         "A public key (pubkey) is required.",
    "auth.pubkey.invalid":          "Invalid public key format. Expected 64 hex characters.",
    "auth.success":                 "Authentication successful.",
    "auth.failure":                 "Authentication failed. Please check your credentials.",
    "auth.session.created":         "Session created. You are now logged in.",
    "auth.session.invalid":         "Session token is invalid or has expired.",
    "auth.session.expired":         "Your session has expired. Please log in again.",
    "auth.session.revoked":         "Session revoked successfully.",
    "auth.session.not_found":       "Session not found.",
    "auth.rate_limited":            "Too many authentication attempts. Please wait {wait_seconds} seconds.",
    "auth.nostr.event.required":    "A signed Nostr event is required.",
    "auth.nostr.event.invalid":     "The signed Nostr event is invalid.",
    "auth.nostr.pubkey.mismatch":   "The event pubkey does not match the requested public key.",
    "auth.lnurl.challenge.invalid": "LNURL authentication challenge is invalid.",
    "auth.lnurl.signature.invalid": "LNURL signature verification failed.",
    "auth.permission.denied":       "You do not have permission to perform this action.",

    # -----------------------------------------------------------------------
    # Savings
    # -----------------------------------------------------------------------
    "savings.goal.set":             "Savings goal updated successfully.",
    "savings.goal.not_found":       "No savings goal configured. Set one to get started.",
    "savings.goal.required":        "A savings goal is required for this action.",
    "savings.deposit.recorded":     "Deposit of {amount} recorded successfully.",
    "savings.deposit.invalid_amount": "Deposit amount must be a positive number.",
    "savings.deposit.not_found":    "Deposit record not found.",
    "savings.projection.generated": "Savings projection generated.",
    "savings.projection.no_data":   "Not enough data to generate a projection. Make at least one deposit.",
    "savings.monthly_target":       "Monthly savings target",
    "savings.total_saved":          "Total saved",
    "savings.total_btc":            "Total BTC accumulated",
    "savings.target_years":         "Target years",
    "savings.on_track":             "You are on track to reach your goal!",
    "savings.behind_target":        "You are currently behind your monthly target.",
    "savings.ahead_target":         "You are ahead of your monthly savings target.",
    "savings.no_deposits":          "No deposits recorded yet. Start saving today!",

    # -----------------------------------------------------------------------
    # Remittance
    # -----------------------------------------------------------------------
    "remittance.calculation.success": "Remittance calculation completed.",
    "remittance.amount.invalid":    "Please enter a valid remittance amount.",
    "remittance.currency.invalid":  "Invalid currency code. Please use a 3-letter ISO code.",
    "remittance.rate.unavailable":  "Exchange rate is temporarily unavailable. Try again shortly.",
    "remittance.fee.breakdown":     "Fee breakdown",
    "remittance.recipient.receives": "Recipient receives",
    "remittance.sender.pays":       "Sender pays",
    "remittance.via_bitcoin":       "Via Bitcoin (instant)",
    "remittance.via_traditional":   "Via traditional wire (3-5 business days)",
    "remittance.savings_vs_traditional": "Savings vs. traditional remittance",
    "remittance.no_data":           "Remittance data is not available at this time.",

    # -----------------------------------------------------------------------
    # Pension
    # -----------------------------------------------------------------------
    "pension.projection.generated": "Pension projection generated.",
    "pension.projection.no_data":   "Please configure your savings goal to generate a pension projection.",
    "pension.age.required":         "Current age is required for pension calculation.",
    "pension.age.invalid":          "Age must be between 18 and 80.",
    "pension.retirement_age":       "Target retirement age",
    "pension.years_to_retire":      "Years until retirement",
    "pension.projected_value":      "Projected portfolio value at retirement",
    "pension.monthly_income":       "Estimated monthly income",
    "pension.inflation_adjusted":   "Inflation-adjusted value",
    "pension.on_track":             "You are on track for a comfortable retirement.",
    "pension.underfunded":          "Your current savings rate may not meet your retirement goal.",
    "pension.increase_savings":     "Consider increasing your monthly savings to meet your goal.",

    # -----------------------------------------------------------------------
    # Market
    # -----------------------------------------------------------------------
    "market.price.unavailable":     "Bitcoin price data is temporarily unavailable.",
    "market.price.fetched":         "Market price retrieved successfully.",
    "market.fees.unavailable":      "On-chain fee data is temporarily unavailable.",
    "market.fees.fetched":          "Fee estimates retrieved successfully.",
    "market.history.unavailable":   "Price history is temporarily unavailable.",
    "market.history.fetched":       "Price history retrieved successfully.",
    "market.loading":               "Loading market data…",
    "market.last_updated":          "Last updated",

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------
    "alerts.preferences.updated":  "Alert preferences updated.",
    "alerts.preferences.not_found": "No alert preferences found. Using defaults.",
    "alerts.fee.triggered":         "Bitcoin fee alert: {direction} {level} sat/vB",
    "alerts.price.triggered":       "Bitcoin price alert: {direction} {price}",
    "alerts.fee.high":              "Fees are HIGH — currently {fee} sat/vB.",
    "alerts.fee.low":               "Fees are LOW — currently {fee} sat/vB. Good time to transact!",
    "alerts.price.above":           "BTC price crossed above {threshold}.",
    "alerts.price.below":           "BTC price dropped below {threshold}.",
    "alerts.enabled":               "Alerts are enabled.",
    "alerts.disabled":              "Alerts are disabled.",

    # -----------------------------------------------------------------------
    # Achievements
    # -----------------------------------------------------------------------
    "achievements.earned":          "Achievement unlocked: {name}!",
    "achievements.none":            "No achievements yet. Start saving to earn your first badge!",
    "achievements.all_fetched":     "Achievements loaded.",

    # Achievement names
    "achievement.first_deposit.name":       "First Steps",
    "achievement.first_deposit.desc":       "Made your first Bitcoin savings deposit.",
    "achievement.hodl_week.name":           "Week HODLer",
    "achievement.hodl_week.desc":           "Saved consistently for an entire week.",
    "achievement.hodl_month.name":          "Monthly Stacker",
    "achievement.hodl_month.desc":          "Maintained your savings habit for 30 days.",
    "achievement.goal_setter.name":         "Goal Setter",
    "achievement.goal_setter.desc":         "Set your first savings goal.",
    "achievement.diamond_hands.name":       "Diamond Hands",
    "achievement.diamond_hands.desc":       "Held your Bitcoin through a 10% market dip.",
    "achievement.satoshi_100k.name":        "100K Sats",
    "achievement.satoshi_100k.desc":        "Accumulated 100,000 satoshis.",
    "achievement.satoshi_1m.name":          "1M Sats",
    "achievement.satoshi_1m.desc":          "Accumulated 1,000,000 satoshis.",
    "achievement.satoshi_10m.name":         "10M Sats",
    "achievement.satoshi_10m.desc":         "Accumulated 10,000,000 satoshis.",
    "achievement.on_track.name":            "On Track",
    "achievement.on_track.desc":            "Stayed on track with your savings plan for a full month.",
    "achievement.nostr_auth.name":          "Nostr Native",
    "achievement.nostr_auth.desc":          "Authenticated using Nostr (NIP-07).",
    "achievement.streak_7.name":            "7-Day Streak",
    "achievement.streak_7.desc":            "Deposited every day for 7 consecutive days.",
    "achievement.streak_30.name":           "30-Day Streak",
    "achievement.streak_30.desc":           "Deposited every day for 30 consecutive days.",
    "achievement.early_adopter.name":       "Early Adopter",
    "achievement.early_adopter.desc":       "One of the first 100 users on Magma.",
    "achievement.big_saver.name":           "Big Saver",
    "achievement.big_saver.desc":           "Saved over $500 in a single month.",
    "achievement.lightning_fast.name":      "Lightning Fast",
    "achievement.lightning_fast.desc":      "Completed a Lightning Network payment.",

    # -----------------------------------------------------------------------
    # Notifications
    # -----------------------------------------------------------------------
    "notification.welcome.title":       "Welcome to Magma!",
    "notification.welcome.body":        "Start your Bitcoin savings journey today. Set a goal and make your first deposit.",
    "notification.deposit.title":       "Deposit Confirmed",
    "notification.deposit.body":        "Your deposit of {amount} has been recorded. You've saved {total} so far.",
    "notification.achievement.title":   "Achievement Unlocked!",
    "notification.achievement.body":    'You earned the "{name}" badge. Keep stacking!',
    "notification.goal_reached.title":  "Savings Goal Reached!",
    "notification.goal_reached.body":   "Congratulations! You have reached your savings goal of {goal}.",
    "notification.price_alert.title":   "Bitcoin Price Alert",
    "notification.price_alert.body":    "BTC is now {direction} {threshold}. Current price: {price}.",
    "notification.fee_alert.title":     "Fee Alert",
    "notification.fee_alert.body":      "On-chain fees are now {level}: {fee} sat/vB.",
    "notification.streak.title":        "Savings Streak!",
    "notification.streak.body":         "You are on a {days}-day savings streak. Don't break it!",
    "notification.monthly_summary.title": "Monthly Summary",
    "notification.monthly_summary.body":  "This month you saved {amount}. Your total is now {total}.",

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------
    "export.generated":             "Export generated successfully.",
    "export.format.pdf":            "PDF Export",
    "export.format.csv":            "CSV Export",
    "export.format.json":           "JSON Export",
    "export.no_data":               "No data available to export.",
    "export.savings_report":        "Savings Report",
    "export.remittance_report":     "Remittance Report",
    "export.pension_report":        "Pension Projection Report",
    "export.generated_by":          "Generated by Magma",
    "export.generated_on":          "Generated on",
    "export.confidential":          "Confidential — for personal use only.",

    # -----------------------------------------------------------------------
    # Compliance / Admin
    # -----------------------------------------------------------------------
    "compliance.aml.low":           "Low risk transaction.",
    "compliance.aml.medium":        "Medium risk — monitoring required.",
    "compliance.aml.high":          "High risk — manual review required.",
    "compliance.aml.critical":      "Critical risk — transaction blocked pending review.",
    "compliance.ctr.required":      "Currency Transaction Report required for ${amount}.",
    "compliance.sar.drafted":       "Suspicious Activity Report drafted.",
    "compliance.alert.pending":     "Compliance alert pending review.",
    "compliance.alert.resolved":    "Compliance alert resolved.",
    "compliance.sanctioned_address": "This address is on a sanctions list. Transaction blocked.",
    "compliance.jurisdiction.sv":   "El Salvador (UAF)",
    "compliance.jurisdiction.us":   "United States (FinCEN)",
    "compliance.jurisdiction.eu":   "European Union (EBA)",

    "admin.access.denied":          "Admin access denied.",
    "admin.access.not_configured":  "Admin access is not configured on this server.",
    "admin.action.completed":       "Admin action completed successfully.",
    "admin.user.banned":            "User {pubkey} has been banned.",
    "admin.user.unbanned":          "User {pubkey} ban has been lifted.",
    "admin.maintenance.completed":  "Maintenance completed in {elapsed_ms}ms.",
    "admin.config.updated":         "Configuration key '{key}' updated.",
    "admin.config.blocked":         "Configuration key '{key}' cannot be modified at runtime.",

    # -----------------------------------------------------------------------
    # Errors
    # -----------------------------------------------------------------------
    "error.not_found":              "The requested resource was not found.",
    "error.bad_request":            "The request is malformed or missing required fields.",
    "error.unauthorized":           "Authentication is required.",
    "error.forbidden":              "You do not have permission to access this resource.",
    "error.rate_limited":           "Too many requests. Please slow down.",
    "error.internal":               "An internal server error occurred. Please try again.",
    "error.database":               "A database error occurred. Please contact support.",
    "error.validation.string":      "Field '{field}' must be a string.",
    "error.validation.number":      "Field '{field}' must be a number.",
    "error.validation.range":       "Field '{field}' must be between {min} and {max}.",
    "error.validation.required":    "Field '{field}' is required.",
    "error.validation.invalid":     "Field '{field}' has an invalid value.",
    "error.injection.detected":     "Potentially malicious input detected in field '{field}'.",
    "error.sanitization.failed":    "Input could not be sanitized for field '{field}'.",
    "error.method.not_allowed":     "HTTP method not allowed for this endpoint.",
    "error.payload.too_large":      "Request payload exceeds the maximum allowed size.",
    "error.timeout":                "The request timed out. Please try again.",
    "error.service.unavailable":    "This service is temporarily unavailable.",
    "error.bitcoin.address":        "Invalid Bitcoin address.",
    "error.lightning.invoice":      "Invalid Lightning Network invoice.",
    "error.nostr.pubkey":           "Invalid Nostr public key.",
    "error.amount.negative":        "Amount cannot be negative.",
    "error.amount.zero":            "Amount cannot be zero.",
    "error.amount.too_large":       "Amount exceeds the maximum allowed value.",
    "error.date.invalid":           "Invalid date format. Expected YYYY-MM-DD.",
    "error.currency.invalid":       "Invalid currency code.",
    "error.json.invalid":           "Invalid JSON payload.",

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------
    "portfolio.summary":            "Portfolio Summary",
    "portfolio.current_value":      "Current portfolio value",
    "portfolio.total_invested":     "Total amount invested",
    "portfolio.unrealized_gain":    "Unrealized gain/loss",
    "portfolio.return_pct":         "Total return",
    "portfolio.btc_price_avg":      "Average buy price",
    "portfolio.holdings":           "Holdings",
    "portfolio.no_data":            "No portfolio data available. Make your first deposit to get started.",

    # -----------------------------------------------------------------------
    # General UI
    # -----------------------------------------------------------------------
    "general.loading":              "Loading…",
    "general.saving":               "Saving…",
    "general.success":              "Success!",
    "general.error":                "An error occurred.",
    "general.cancel":               "Cancel",
    "general.confirm":              "Confirm",
    "general.save":                 "Save",
    "general.delete":               "Delete",
    "general.edit":                 "Edit",
    "general.view":                 "View",
    "general.back":                 "Back",
    "general.next":                 "Next",
    "general.previous":             "Previous",
    "general.close":                "Close",
    "general.search":               "Search",
    "general.filter":               "Filter",
    "general.sort":                 "Sort",
    "general.export":               "Export",
    "general.import":               "Import",
    "general.refresh":              "Refresh",
    "general.yes":                  "Yes",
    "general.no":                   "No",
    "general.none":                 "None",
    "general.all":                  "All",
    "general.today":                "Today",
    "general.yesterday":            "Yesterday",
    "general.this_week":            "This week",
    "general.this_month":           "This month",
    "general.days_ago":             "{n} days ago",
    "general.hours_ago":            "{n} hours ago",
    "general.minutes_ago":          "{n} minutes ago",
    "general.just_now":             "Just now",
    "general.unknown":              "Unknown",
    "general.n_a":                  "N/A",
}
