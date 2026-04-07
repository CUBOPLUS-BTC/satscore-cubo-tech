import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/score_gauge.dart';
import '../../../shared/widgets/breakdown_bar.dart';
import '../../../shared/widgets/btc_address_input.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../providers/score_provider.dart';

class ScoreScreen extends ConsumerWidget {
  const ScoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(scoreProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          BTCAddressInput(
            onSubmit: (address) =>
                ref.read(scoreProvider.notifier).calculateScore(address),
            isLoading: state.isLoading,
          ),
          const SizedBox(height: 24),
          if (state.error != null) _buildError(context, ref, state.error!),
          if (state.isLoading) _buildLoading(),
          if (state.result == null && !state.isLoading && state.error == null)
            _buildEmpty(),
          if (state.result != null && !state.isLoading) _buildResult(state),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Padding(
      padding: const EdgeInsets.only(top: 48),
      child: Column(
        children: [
          Text('Bitcoin Score', style: AppTypography.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Enter a Bitcoin address above to get your financial health score',
            style: AppTypography.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildLoading() {
    return Padding(
      padding: const EdgeInsets.only(top: 32),
      child: Column(
        children: [
          Center(child: LoadingShimmer.gauge()),
          const SizedBox(height: 16),
          LoadingShimmer.card(height: 48),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 48),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 48),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, WidgetRef ref, String error) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.danger.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.danger.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 20, color: AppColors.danger),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              error,
              style: AppTypography.bodyMedium.copyWith(color: AppColors.danger),
            ),
          ),
          TextButton(
            onPressed: () => ref.read(scoreProvider.notifier).reset(),
            child: Text(
              'Retry',
              style: AppTypography.titleSmall.copyWith(color: AppColors.accent),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResult(ScoreState state) {
    final result = state.result!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 24),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: Column(
            children: [
              ScoreGauge(score: result.totalScore),
              const SizedBox(height: 4),
              Text('of 750 possible', style: AppTypography.bodySmall),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  result.address,
                  style: AppTypography.monoSmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Text('Breakdown', style: AppTypography.titleSmall),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: Column(
            children: [
              BreakdownBar(
                label: 'Consistency',
                score: result.breakdown.consistency.score,
                maxScore: result.breakdown.consistency.max,
              ),
              const SizedBox(height: 12),
              BreakdownBar(
                label: 'Volume',
                score: result.breakdown.relativeVolume.score,
                maxScore: result.breakdown.relativeVolume.max,
              ),
              const SizedBox(height: 12),
              BreakdownBar(
                label: 'Diversification',
                score: result.breakdown.diversification.score,
                maxScore: result.breakdown.diversification.max,
              ),
              const SizedBox(height: 12),
              BreakdownBar(
                label: 'Savings',
                score: result.breakdown.savingsPattern.score,
                maxScore: result.breakdown.savingsPattern.max,
              ),
              const SizedBox(height: 12),
              BreakdownBar(
                label: 'Payment History',
                score: result.breakdown.paymentHistory.score,
                maxScore: result.breakdown.paymentHistory.max,
              ),
              const SizedBox(height: 12),
              BreakdownBar(
                label: 'Lightning',
                score: result.breakdown.lightningActivity.score,
                maxScore: result.breakdown.lightningActivity.max,
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Text('Recommendations', style: AppTypography.titleSmall),
        const SizedBox(height: 12),
        ...result.recommendations.asMap().entries.map((entry) {
          final colors = [AppColors.accent, AppColors.info, AppColors.success];
          final color = colors[entry.key % colors.length];
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border(
                  left: BorderSide(color: color, width: 3),
                  top: BorderSide(color: AppColors.borderSubtle),
                  right: BorderSide(color: AppColors.borderSubtle),
                  bottom: BorderSide(color: AppColors.borderSubtle),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Icon(Icons.arrow_forward, size: 14, color: color),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(entry.value, style: AppTypography.bodyMedium),
                  ),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }
}
