import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/main.dart';

void main() {
  testWidgets('shows marketplace shell', (tester) async {
    await tester.pumpWidget(const SouthOmoMarketApp());
    expect(find.text('South Omo Market'), findsOneWidget);
  });
}
