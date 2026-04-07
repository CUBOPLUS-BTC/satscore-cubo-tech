import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/api_exceptions.dart';
import '../../../core/models/simulation.dart';
import '../data/simulator_repository.dart';

class SimulatorState {
  final SimulationResult? result;
  final bool isLoading;
  final String? error;

  const SimulatorState({this.result, this.isLoading = false, this.error});
}

class SimulatorNotifier extends Notifier<SimulatorState> {
  @override
  SimulatorState build() => const SimulatorState();

  Future<void> simulate(double amountUsd, int daysHistory) async {
    state = const SimulatorState(isLoading: true);
    try {
      final repo = ref.read(simulatorRepositoryProvider);
      final result = await repo.simulateVolatility(
        amountUsd: amountUsd,
        daysHistory: daysHistory,
      );
      state = SimulatorState(result: result);
    } on ApiException catch (e) {
      state = SimulatorState(error: e.message);
    } catch (e) {
      state = SimulatorState(error: 'Failed to simulate');
    }
  }
}

final simulatorProvider = NotifierProvider<SimulatorNotifier, SimulatorState>(
  SimulatorNotifier.new,
);
