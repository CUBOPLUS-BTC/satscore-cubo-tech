import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/api_exceptions.dart';
import '../../../core/models/remittance.dart';
import '../data/remittance_repository.dart';

class RemittanceState {
  final RemittanceResult? result;
  final bool isLoading;
  final String? error;

  const RemittanceState({this.result, this.isLoading = false, this.error});
}

class RemittanceNotifier extends Notifier<RemittanceState> {
  @override
  RemittanceState build() => const RemittanceState();

  Future<void> compare(double amountUsd, String frequency) async {
    state = const RemittanceState(isLoading: true);
    try {
      final repo = ref.read(remittanceRepositoryProvider);
      final result = await repo.compareChannels(
        amountUsd: amountUsd,
        frequency: frequency,
      );
      state = RemittanceState(result: result);
    } on ApiException catch (e) {
      state = RemittanceState(error: e.message);
    } catch (e) {
      state = RemittanceState(error: 'Failed to compare channels');
    }
  }
}

final remittanceProvider =
    NotifierProvider<RemittanceNotifier, RemittanceState>(
      RemittanceNotifier.new,
    );
