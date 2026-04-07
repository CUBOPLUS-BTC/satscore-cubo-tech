import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/api_exceptions.dart';
import '../../../core/models/score_result.dart';
import '../data/score_repository.dart';

class ScoreState {
  final ScoreResult? result;
  final bool isLoading;
  final String? error;

  const ScoreState({this.result, this.isLoading = false, this.error});
}

class ScoreNotifier extends Notifier<ScoreState> {
  @override
  ScoreState build() => const ScoreState();

  Future<void> calculateScore(String address) async {
    state = const ScoreState(isLoading: true);
    try {
      final repo = ref.read(scoreRepositoryProvider);
      final result = await repo.fetchScore(address);
      state = ScoreState(result: result);
    } on ApiException catch (e) {
      state = ScoreState(error: e.message);
    } catch (e) {
      state = ScoreState(error: 'Failed to calculate score');
    }
  }

  void reset() {
    state = const ScoreState();
  }
}

final scoreProvider = NotifierProvider<ScoreNotifier, ScoreState>(
  ScoreNotifier.new,
);
