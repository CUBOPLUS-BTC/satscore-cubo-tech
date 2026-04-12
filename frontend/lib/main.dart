import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'i18n/translations.g.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  LocaleSettings.useDeviceLocale();
  runApp(
    TranslationProvider(
      translations: $currentLocale == AppLocale.es ? esTranslations : enTranslations,
      child: const ProviderScope(child: SatsScoreApp()),
    ),
  );
}
