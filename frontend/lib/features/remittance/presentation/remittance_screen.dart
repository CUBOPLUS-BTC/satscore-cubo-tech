import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/models/remittance.dart';
import '../../../shared/widgets/channel_card.dart';
import '../../../shared/widgets/savings_card.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../providers/remittance_provider.dart';

class RemittanceScreen extends ConsumerStatefulWidget {
  const RemittanceScreen({super.key});

  @override
  ConsumerState<RemittanceScreen> createState() => _RemittanceScreenState();
}

class _RemittanceScreenState extends ConsumerState<RemittanceScreen> {
  final _amountController = TextEditingController();
  String _frequency = 'monthly';

  static const _frequencyOptions = ['Monthly', 'Biweekly', 'Weekly'];

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  void _handleCompare() {
    final amountText = _amountController.text.trim();
    if (amountText.isEmpty) return;

    final amount = double.tryParse(amountText);
    if (amount == null || amount <= 0) return;

    ref.read(remittanceProvider.notifier).compare(amount, _frequency);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(remittanceProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInputSection(),
          const SizedBox(height: 16),
          _buildCompareButton(state.isLoading),
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
            child: DropdownButton<String>(
              value: _frequency,
              dropdownColor: AppColors.surfaceElevated,
              style: AppTypography.mono,
              items: _frequencyOptions
                  .map(
                    (f) => DropdownMenuItem(
                      value: f.toLowerCase(),
                      child: Text(
                        f,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => _frequency = v);
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCompareButton(bool isLoading) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        onPressed: isLoading ? null : _handleCompare,
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
                'Compare Channels',
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
          Text('Save on every transfer', style: AppTypography.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Compare fees across Lightning, on-chain,\nand traditional transfer methods',
            style: AppTypography.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.borderSubtle),
            ),
            child: Column(
              children: [
                _emptyChannelRow(
                  'Lightning Network',
                  '< 1 min',
                  '~0.5%',
                  AppColors.accent,
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Divider(height: 1, color: AppColors.borderSubtle),
                ),
                _emptyChannelRow(
                  'Bitcoin On-chain',
                  '~30 min',
                  '~1.2%',
                  AppColors.info,
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Divider(height: 1, color: AppColors.borderSubtle),
                ),
                _emptyChannelRow(
                  'Traditional',
                  '1-5 days',
                  '5-8%',
                  AppColors.danger,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _emptyChannelRow(String name, String time, String fee, Color color) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(child: Text(name, style: AppTypography.titleSmall)),
        Text(time, style: AppTypography.bodySmall),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            fee,
            style: AppTypography.monoSmall.copyWith(color: color),
          ),
        ),
      ],
    );
  }

  Widget _buildLoading() {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        children: [
          LoadingShimmer.card(height: 80),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 72),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 72),
          const SizedBox(height: 8),
          LoadingShimmer.card(height: 72),
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
              ref.read(remittanceProvider.notifier).compare(amount, _frequency);
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

  Widget _buildResult(RemittanceState state) {
    final result = state.result!;
    final amount = double.tryParse(_amountController.text.trim()) ?? 500;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SavingsCard(
          annualSavings: result.annualSavings,
          vsChannel: 'worst channel',
          monthlyAmount: amount,
        ),
        const SizedBox(height: 16),
        Text('Channels', style: AppTypography.titleSmall),
        const SizedBox(height: 8),
        ...result.channels.map(
          (channel) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: ChannelCard(channel: channel),
          ),
        ),
        if (result.bestTime != null) ...[
          const SizedBox(height: 12),
          _buildBestTimeCard(result.bestTime!),
        ],
      ],
    );
  }

  Widget _buildBestTimeCard(SendTimeRecommendation bestTime) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: AppColors.info.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.access_time,
                  size: 16,
                  color: AppColors.info,
                ),
              ),
              const SizedBox(width: 8),
              Text('Best Time to Send', style: AppTypography.titleSmall),
            ],
          ),
          const SizedBox(height: 12),
          Text(bestTime.bestTime, style: AppTypography.bodyLarge),
          const SizedBox(height: 8),
          Row(
            children: [
              _feeTag(
                'Current',
                Formatters.formatSatVb(bestTime.currentFeeSatVb),
                AppColors.textSecondary,
              ),
              const SizedBox(width: 8),
              _feeTag(
                'Low',
                Formatters.formatSatVb(bestTime.estimatedLowFeeSatVb),
                AppColors.success,
              ),
              const SizedBox(width: 8),
              _feeTag(
                'Save',
                '${bestTime.savingsPercent.toStringAsFixed(0)}%',
                AppColors.success,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _feeTag(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(4),
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
}
