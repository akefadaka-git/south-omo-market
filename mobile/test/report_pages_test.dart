import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/features/marketplace/listing_detail_page.dart';
import 'package:south_omo_market/features/marketplace/my_reports_page.dart';

void main() {
  testWidgets('buyer can report a listing with evidence through the real API contract', (tester) async {
    var reportBody = <String, dynamic>{};
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/listing-report')) {
        return http.Response(jsonEncode({
          'id': 'listing-report', 'seller_id': 'seller-profile-1',
          'title': 'Synthetic listing', 'description': 'Test-only item',
          'price_minor': 10000, 'location': 'Koybe', 'images': [],
        }), 200);
      }
      if (request.url.path.endsWith('/auth/register')) {
        return http.Response('{"id":"buyer-report"}', 201);
      }
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response('{"access_token":"synthetic-report-token"}', 200);
      }
      if (request.url.path.endsWith('/reports') && request.method == 'POST') {
        reportBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response('{"id":"report-1","status":"pending"}', 201);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: ListingDetailPage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      client: client,
      listingId: 'listing-report',
    )));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Report listing'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('buyer-display-name')), 'Synthetic reporter');
    await tester.enterText(find.byKey(const Key('buyer-phone')), '+251900000801');
    await tester.enterText(find.byKey(const Key('buyer-password')), 'synthetic-report-password-801');
    await tester.tap(find.text('Register and continue'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextFormField).first,
      'The advertised details do not match the item being offered.');
    await tester.enterText(find.byType(TextFormField).at(1),
      'Evidence: seller message describes a different item.');
    await tester.enterText(find.byType(TextFormField).at(2), 'case-reference-801');
    await tester.tap(find.text('Submit report'));
    await tester.pumpAndSettle();

    expect(reportBody['listing_id'], 'listing-report');
    expect(reportBody['reason'], 'misleading_information');
    expect((reportBody['evidence'] as List).single['summary'],
      'Evidence: seller message describes a different item.');
    expect(find.textContaining('Report submitted'), findsOneWidget);
    client.close();
  });

  testWidgets('report submission errors do not hide listing details', (tester) async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/listing-error')) {
        return http.Response(jsonEncode({
          'id': 'listing-error', 'seller_id': 'seller-profile-1',
          'title': 'Synthetic listing remains visible', 'description': 'Test-only item',
          'price_minor': 10000, 'location': 'Koybe', 'images': [],
        }), 200);
      }
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response('{"access_token":"synthetic-report-token"}', 200);
      }
      if (request.url.path.endsWith('/reports') && request.method == 'POST') {
        return http.Response(jsonEncode({'detail': 'Report service temporarily unavailable.'}), 503);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: ListingDetailPage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      client: client,
      listingId: 'listing-error',
    )));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Report listing'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('buyer-phone')), '+251900000802');
    await tester.enterText(find.byKey(const Key('buyer-password')), 'synthetic-report-password-802');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).first,
      'The listing contains a materially false claim about the item.');
    await tester.tap(find.text('Submit report'));
    await tester.pumpAndSettle();

    expect(find.text('Synthetic listing remains visible'), findsOneWidget);
    expect(find.textContaining('Report service temporarily unavailable.'), findsOneWidget);
    client.close();
  });

  testWidgets('my reports page shows private status and review note', (tester) async {
    final client = MockClient((request) async {
      expect(request.headers['Authorization'], 'Bearer report-access-token');
      expect(request.url.path.endsWith('/reports/my'), isTrue);
      return http.Response(jsonEncode([
        {
          'id': 'report-2', 'listing_id': 'listing-2', 'seller_id': null,
          'reason': 'fraud', 'description': 'Synthetic report description',
          'status': 'in_review', 'review_note': 'A moderator is reviewing this report.',
          'created_at': '2026-11-21T10:00:00Z',
        },
      ]), 200);
    });

    await tester.pumpWidget(MaterialApp(home: MyReportsPage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      client: client,
      accessToken: 'report-access-token',
    )));
    await tester.pumpAndSettle();

    expect(find.text('My reports'), findsOneWidget);
    expect(find.text('Listing report'), findsOneWidget);
    expect(find.text('Under review'), findsOneWidget);
    expect(find.textContaining('A moderator is reviewing this report.'), findsOneWidget);
    client.close();
  });
}
