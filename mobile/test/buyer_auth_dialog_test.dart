import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
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
          {'id': 'town-koybe', 'level': 'town', 'name': 'ቆይቤ', 'name_en': 'Koybe', 'name_am': 'ቆይቤ'},
        ]), 200);
      }
      if (request.url.path.endsWith('/markets')) {
        return http.Response(jsonEncode([
          {'id': 'market-koybe', 'location_id': 'town-koybe', 'name': 'ቆይቤ ገበያ', 'name_en': 'Koybe market', 'name_am': 'ቆይቤ ገበያ'},
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
      locale: const Locale('am'),
      supportedLocales: const [Locale('am'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
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
    await tester.tap(find.byKey(const Key('buyer-registration-toggle')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('buyer-account-type')), findsOneWidget);
    expect(find.byKey(const Key('buyer-preferred-location')), findsOneWidget);
    expect(find.text('የሚመርጡት አካባቢ (አስፈላጊ)'), findsOneWidget);
    final areaDropdown = tester.widget<DropdownButton<String>>(
      find.descendant(
        of: find.byKey(const Key('buyer-preferred-location')),
        matching: find.byType(DropdownButton<String>),
      ),
    );
    expect(areaDropdown.dropdownColor, Colors.white);
    expect(areaDropdown.style?.color, const Color(0xFF102B2A));
    expect(find.byKey(const Key('buyer-preferred-language')), findsOneWidget);
    await tester.tap(find.byKey(const Key('buyer-account-type')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('ጅምላ አከፋፋይ').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('buyer-display-name')), 'Synthetic Buyer');
    await tester.enterText(find.byKey(const Key('buyer-phone')), '+251900000901');
    await tester.enterText(find.byKey(const Key('buyer-password')), 'synthetic-password-901');

    await tester.tap(find.byKey(const Key('buyer-register-submit')));
    await tester.pumpAndSettle();
    expect(registrationBody, isNull,
        reason: 'Registration must be blocked until a preferred locality is selected');

    await tester.ensureVisible(find.byKey(const Key('buyer-preferred-location')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('buyer-preferred-location')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('ቆይቤ').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('buyer-preferred-market')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('buyer-preferred-market')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('ቆይቤ ገበያ').last);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('buyer-register-submit')));
    await tester.pumpAndSettle();

    expect(registrationBody?['phone_number'], '+251900000901');
    expect(registrationBody?['preferred_location_id'], 'town-koybe');
    expect(registrationBody?['preferred_market_id'], 'market-koybe');
    expect(registrationBody?['preferred_language'], 'am');
    expect(registrationBody?['account_type'], 'bulk_distributor');
    expect(loginRequested, isTrue);
    expect(find.text('Create buyer account'), findsNothing);
    client.close();
  });
}
