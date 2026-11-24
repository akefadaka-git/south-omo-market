import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:south_omo_market/features/marketplace/buyer_auth_dialog.dart';

void main() {
  testWidgets('buyer registration requires locality and sends preferences to API', (tester) async {
    Map<String, dynamic>? registrationBody;
    var loginRequested = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/locations')) {
        return http.Response(jsonEncode([
          {'id': 'town-koybe', 'level': 'town', 'name': 'Koybe', 'name_en': 'Koybe'},
        ]), 200);
      }
      if (request.url.path.endsWith('/markets')) {
        return http.Response(jsonEncode([
          {'id': 'market-koybe', 'location_id': 'town-koybe', 'name': 'Koybe market'},
        ]), 200);
      }
      if (request.url.path.endsWith('/auth/register')) {
        registrationBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response('{"id":"synthetic-user"}', 201);
      }
      if (request.url.path.endsWith('/auth/login')) {
        loginRequested = true;
        return http.Response('{"access_token":"synthetic-token","token_type":"bearer"}', 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (context) => TextButton(
          onPressed: () => showDialog<String>(
            context: context,
            builder: (_) => BuyerAuthDialog(
              apiBaseUrl: 'https://market.example.test/api/v1',
              client: client,
            ),
          ),
          child: const Text('Open buyer sign in'),
        )),
      ),
    ));
    await tester.tap(find.text('Open buyer sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('buyer-preferred-location')), findsOneWidget);
    expect(find.byKey(const Key('buyer-preferred-language')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('buyer-display-name')), 'Synthetic Buyer');
    await tester.enterText(find.byKey(const Key('buyer-phone')), '+251900000901');
    await tester.enterText(find.byKey(const Key('buyer-password')), 'synthetic-password-901');

    await tester.tap(find.text('Register and continue'));
    await tester.pumpAndSettle();
    expect(registrationBody, isNull,
        reason: 'Registration must be blocked until a preferred locality is selected');

    await tester.tap(find.byKey(const Key('buyer-preferred-location')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Koybe').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('buyer-preferred-market')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Koybe market').last);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Register and continue'));
    await tester.pumpAndSettle();

    expect(registrationBody?['phone_number'], '+251900000901');
    expect(registrationBody?['preferred_location_id'], 'town-koybe');
    expect(registrationBody?['preferred_market_id'], 'market-koybe');
    expect(registrationBody?['preferred_language'], 'am');
    expect(loginRequested, isTrue);
    expect(find.text('Create buyer account'), findsNothing);
    client.close();
  });
}
