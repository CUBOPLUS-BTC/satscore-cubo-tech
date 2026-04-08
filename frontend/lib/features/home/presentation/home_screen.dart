import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../providers/price_provider.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final priceAsync = ref.watch(priceProvider);

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _BalanceHero(priceAsync: priceAsync),
            const SizedBox(height: 24),
            _ToolsGrid(context: context),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _BalanceHero extends ConsumerWidget {
  final AsyncValue priceAsync;

  const _BalanceHero({required this.priceAsync});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
      child: Column(
        children: [
          Text(
            'BTC/USD',
            style: AppTypography.labelLarge.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          priceAsync.when(
            data: (price) {
              return Column(
                children: [
                  Text(
                    Formatters.formatUSD(price.priceUsd),
                    style: AppTypography.displayLarge.copyWith(
                      fontSize: 32,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Bitcoin Price',
                    style: AppTypography.mono.copyWith(
                      color: AppColors.textSecondary,
                      fontSize: 14,
                    ),
                  ),
                ],
              );
            },
            loading: () => Column(
              children: [
                const LoadingShimmer(width: 160, height: 32),
                const SizedBox(height: 8),
                LoadingShimmer.text(width: 140),
              ],
            ),
            error: (err, _) => Column(
              children: [
                Text(
                  'Unable to load price',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => ref.invalidate(priceProvider),
                  child: Text(
                    'Retry',
                    style: AppTypography.labelLarge.copyWith(
                      color: AppColors.accent,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ToolsGrid extends StatelessWidget {
  final BuildContext context;

  const _ToolsGrid({required this.context});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _ToolCard(
                icon: Icons.analytics_outlined,
                title: 'Score',
                subtitle: 'Address health analysis',
                accentColor: AppColors.accent,
                onTap: () => context.go('/score'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _ToolCard(
                icon: Icons.candlestick_chart_outlined,
                title: 'Simulator',
                subtitle: 'Volatility & timing',
                accentColor: AppColors.primary,
                onTap: () => context.go('/simulator'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        _ToolCardWide(
          icon: Icons.route_outlined,
          title: 'Remittance Optimizer',
          subtitle: 'Compare Lightning, on-chain, and traditional channels',
          accentColor: AppColors.success,
          onTap: () => context.go('/remittance'),
        ),
      ],
    );
  }
}

class _ToolCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color accentColor;
  final VoidCallback onTap;

  const _ToolCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accentColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 20, color: accentColor),
              const SizedBox(height: 12),
              Text(
                title,
                style: AppTypography.titleSmall.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(subtitle, style: AppTypography.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _ToolCardWide extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color accentColor;
  final VoidCallback onTap;

  const _ToolCardWide({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accentColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
          ),
          child: Row(
            children: [
              Icon(icon, size: 20, color: accentColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTypography.titleSmall.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(subtitle, style: AppTypography.bodySmall),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                size: 20,
                color: AppColors.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
