import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/models/simulation.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../../../shared/widgets/risk_chart.dart';
import '../providers/simulator_provider.dart';

class SimulatorScreen extends ConsumerStatefulWidget {
  const SimulatorScreen({super.key});

  @override
  ConsumerState<SimulatorScreen> createState() => _SimulatorScreenState();
}

class _SimulatorScreenState extends ConsumerState<SimulatorScreen> {
  final _amountController = TextEditingController();
  int _period = 90;

  static const _periodOptions = {
    '30 days': 30,
    '90 days': 90,
    '180 days': 180,
    '1 year': 365,
  };

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  void _handleSimulate() {
    final amountText = _amountController.text.trim();
    if (amountText.isEmpty) return;

    final amount = double.tryParse(amountText);
    if (amount == null || amount <= 0) return;

    ref.read(simulatorProvider.notifier).simulate(amount, _period);
  }

  Color _riskColor(String riskZone) {
    switch (riskZone.toLowerCase()) {
      case 'low':
        return AppColors.success;
      case 'medium':
        return AppColors.warning;
      case 'high':
        return AppColors.danger;
      default:
        return AppColors.textTertiary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(simulatorProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInputSection(),
          const SizedBox(height: 16),
          _buildSimulateButton(state.isLoading),
          const SizedBox(height: 24),
          if (state.error != null) _buildError(state.error!),
          if (state.isLoading) _buildLoading(),
          if (state.result == null && !state.isLoading && state.error == null)
            _buildEmpty(),
          if (state.result != null && !state.isLoading) _buildResult(state),
        ],
      ),
    );
  }

  Widget _buildInputSection() {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _amountController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: AppTypography.mono,
            decoration: const InputDecoration(
              hintText: 'Amount',
              prefixText: '\$ ',
            ),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<int>(
              value: _period,
              dropdownColor: AppColors.surfaceElevated,
              style: AppTypography.mono,
              items: _periodOptions.entries
                  .map(
                    (e) => DropdownMenuItem(
                      value: e.value,
                      child: Text(
                        e.key,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => _period = v);
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSimulateButton(bool isLoading) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        onPressed: isLoading ? null : _handleSimulate,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.accent,
          foregroundColor: Colors.black,
          disabledBackgroundColor: AppColors.accent.withValues(alpha: 0.5),
        ),
        child: isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Text(
                'Simulate',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
      ),
    );
  }

  Widget _buildEmpty() {
    return Padding(
      padding: const EdgeInsets.only(top: 32),
      child: Column(
        children: [
          Text('Predict the best moment', style: AppTypography.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Simulate Bitcoin volatility to find when\nto buy, sell, or send with less risk',
            style: AppTypography.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildLoading() {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        children: [
          LoadingShimmer.card(height: 80),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 220),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 200),
        ],
      ),
    );
  }

  Widget _buildError(String error) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.danger.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.danger.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 18, color: AppColors.danger),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              error,
              style: AppTypography.bodyMedium.copyWith(color: AppColors.danger),
            ),
          ),
          TextButton(
            onPressed: () {
              final amountText = _amountController.text.trim();
              if (amountText.isEmpty) return;
              final amount = double.tryParse(amountText);
              if (amount == null || amount <= 0) return;
              ref.read(simulatorProvider.notifier).simulate(amount, _period);
            },
            child: Text(
              'Retry',
              style: AppTypography.labelLarge.copyWith(color: AppColors.accent),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResult(SimulatorState state) {
    final result = state.result!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildRecommendationCard(result),
        const SizedBox(height: 12),
        _buildQuickStats(result),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: RiskChart(data: result.dailyAnalysis),
        ),
        const SizedBox(height: 12),
        _buildDataTable(result),
      ],
    );
  }

  Widget _buildQuickStats(SimulationResult result) {
    return Row(
      children: [
        _statChip('Optimal', '${result.optimalDay}d', AppColors.accent),
        const SizedBox(width: 8),
        _statChip(
          'Expected',
          Formatters.formatPercentage(result.expectedReturn),
          AppColors.success,
        ),
        const SizedBox(width: 8),
        _statChip('Risk', result.riskLevel, _riskColor(result.riskLevel)),
      ],
    );
  }

  Widget _statChip(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withValues(alpha: 0.15)),
        ),
        child: Column(
          children: [
            Text(value, style: AppTypography.mono.copyWith(color: color)),
            const SizedBox(height: 4),
            Text(label, style: AppTypography.labelSmall),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationCard(SimulationResult result) {
    final riskColor = _riskColor(result.riskLevel);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: const Border(
          left: BorderSide(color: AppColors.accent, width: 3),
          top: BorderSide(color: AppColors.borderSubtle),
          right: BorderSide(color: AppColors.borderSubtle),
          bottom: BorderSide(color: AppColors.borderSubtle),
        ),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'RECOMMENDATION',
                style: AppTypography.labelMedium.copyWith(
                  color: AppColors.accent,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  result.riskLevel.toUpperCase(),
                  style: AppTypography.labelSmall.copyWith(color: riskColor),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(result.recommendation, style: AppTypography.bodyLarge),
        ],
      ),
    );
  }

  Widget _buildDataTable(SimulationResult result) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Expanded(
                  flex: 2,
                  child: Text('Day', style: AppTypography.labelMedium),
                ),
                Expanded(
                  flex: 3,
                  child: Text('Avg Return', style: AppTypography.labelMedium),
                ),
                Expanded(
                  flex: 2,
                  child: Text('Risk', style: AppTypography.labelMedium),
                ),
                Expanded(
                  flex: 3,
                  child: Text('Worst Case', style: AppTypography.labelMedium),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.borderSubtle),
          ...result.dailyAnalysis.map<Widget>((day) {
            final isOptimal = day.waitDays == result.optimalDay;
            final riskColor = _riskColor(day.riskZone);

            return Container(
              color: isOptimal
                  ? AppColors.accent.withValues(alpha: 0.08)
                  : null,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: Row(
                      children: [
                        Text(
                          '${day.waitDays}',
                          style: AppTypography.mono.copyWith(
                            color: isOptimal ? AppColors.accent : null,
                          ),
                        ),
                        if (isOptimal)
                          const Padding(
                            padding: EdgeInsets.only(left: 4),
                            child: Icon(
                              Icons.star,
                              size: 12,
                              color: AppColors.accent,
                            ),
                          ),
                      ],
                    ),
                  ),
                  Expanded(
                    flex: 3,
                    child: Text(
                      Formatters.formatPercentage(day.avgReturn),
                      style: AppTypography.mono.copyWith(
                        color: day.avgReturn >= 0
                            ? AppColors.success
                            : AppColors.danger,
                      ),
                    ),
                  ),
                  Expanded(
                    flex: 2,
                    child: Text(
                      day.riskZone,
                      style: AppTypography.monoSmall.copyWith(color: riskColor),
                    ),
                  ),
                  Expanded(
                    flex: 3,
                    child: Text(
                      Formatters.formatPercentage(day.worstCase),
                      style: AppTypography.mono.copyWith(
                        color: AppColors.danger,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
