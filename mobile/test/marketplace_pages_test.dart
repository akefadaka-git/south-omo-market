import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/marketplace_pages.dart';

void main() {
  testWidgets('discovery filters and opens a published listing detail', (tester) async {
    final requests = <String>[];
    final client = MockClient((request) async {
      requests.add('${request.method} ${request.url.path}${request.url.query.isEmpty ? '' : '? ${request.url.query}'}');
      if (request.url.path.endsWith('/categories')) {
        return http.Response(jsonEncode([
          {'id': 'cat-livestock', 'name': 'Livestock'},
        ]), 200);
      }
      if (request.url.path.endsWith('/listings') && request.url.pathSegments.last == 'listings') {
        return http.Response(jsonEncode([
          {'id': 'listing-1', 'title': 'Synthetic goats', 'price_minor': 450000,
           'location': 'Koybe', 'images': []},
        ]), 200);
      }
      if (request.url.path.endsWith('/listings/listing-1')) {
        return http.Response(jsonEncode({
          'id': 'listing-1', 'title': 'Synthetic goats', 'description': 'Test listing',
          'price_minor': 450000, 'location': 'Koybe', 'images': [],
        }), 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: MarketplaceDiscoveryPage(
      apiBaseUrl: 'https://market.example.test/api/v1', client: client,
    )));
    await tester.pumpAndSettle();
    expect(find.text('Synthetic goats'), findsOneWidget);
    await tester.tap(find.text('Synthetic goats'));
    await tester.pumpAndSettle();
    expect(find.text('Listing details'), findsOneWidget);
    expect(find.text('Test listing'), findsOneWidget);
    expect(requests.any((path) => path.contains('/listings/listing-1')), isTrue);
    client.close();
  });

  testWidgets('seller can edit and submit only a server draft', (tester) async {
    var savedTitle = 'Draft cattle';
    var status = 'draft';
    var patchCount = 0;
    var submitCount = 0;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/my')) {
        return http.Response(jsonEncode([
          {'id': 'listing-1', 'category_id': 'cat-1', 'title': savedTitle,
           'description': 'Draft', 'price_minor': 10000, 'location': 'Koybe',
           'status': status, 'images': []},
        ]), 200);
      }
      if (request.url.path.endsWith('/categories')) {
        return http.Response(jsonEncode([
          {'id': 'cat-1', 'name': 'Livestock'},
        ]), 200);
      }
      if (request.method == 'PATCH' && request.url.path.endsWith('/listings/listing-1')) {
        patchCount++;
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        savedTitle = body['title'] as String;
        return http.Response(jsonEncode({
          'id': 'listing-1', 'category_id': 'cat-1', 'title': savedTitle,
          'description': body['description'], 'price_minor': body['price_minor'],
          'location': body['location_label'], 'status': status, 'images': [],
        }), 200);
      }
      if (request.method == 'POST' && request.url.path.endsWith('/listings/listing-1/submit')) {
        submitCount++;
        status = 'pending_review';
        return http.Response(jsonEncode({'id': 'listing-1', 'status': status}), 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: SellerListingsPage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'synthetic-token',
      client: client,
    )));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Draft cattle'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'Updated synthetic cattle');
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();
    expect(patchCount, 1);
    expect(savedTitle, 'Updated synthetic cattle');

    await tester.tap(find.text('Updated synthetic cattle').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Submit for review'));
    await tester.pumpAndSettle();
    expect(submitCount, 1);
    expect(status, 'pending_review');
    expect(find.textContaining('Submitted for moderation'), findsOneWidget);
    client.close();
  });

  testWidgets('buyer can register and send listing inquiry', (tester) async {
    var registered = false;
    var sent = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/listing-2')) {
        return http.Response(jsonEncode({'id':'listing-2','title':'Synthetic maize','description':'Dry maize','price_minor':250000,'location':'Jinka','images':[]}), 200);
      }
      if (request.url.path.endsWith('/auth/register')) {
        registered = true;
        return http.Response('{"id":"buyer-1"}', 201);
      }
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response('{"access_token":"buyer-token"}', 200);
      }
      if (request.url.path.endsWith('/inquiries') && request.method == 'POST') {
        expect(request.headers['authorization'], 'Bearer buyer-token');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['listing_id'], 'listing-2');
        expect(body['message'], 'Is this available?');
        sent = true;
        return http.Response('{"id":"inquiry-1","status":"open"}', 201);
      }
      return http.Response('Not found', 404);
    });
    await tester.pumpWidget(MaterialApp(home: ListingDetailPage(
      apiBaseUrl: 'https://market.example.test/api/v1', client: client, listingId: 'listing-2',
    )));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Is this available?');
    await tester.tap(find.text('Send inquiry'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), 'Buyer Test');
    await tester.enterText(find.byType(TextField).at(1), '+251900000007');
    await tester.enterText(find.byType(TextField).at(2), 'synthetic-password-123');
    await tester.tap(find.text('Register and continue'));
    await tester.pumpAndSettle();
    expect(registered, isTrue);
    expect(sent, isTrue);
    expect(find.text('Your inquiry was sent to the seller.'), findsOneWidget);
    client.close();
  });

}
