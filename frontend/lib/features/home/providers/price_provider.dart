import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/price_data.dart';
import '../data/price_repository.dart';

final priceProvider = FutureProvider.autoDispose<VerifiedPrice>((ref) async {
  final repo = ref.watch(priceRepositoryProvider);
  return repo.fetchPrice();
});
