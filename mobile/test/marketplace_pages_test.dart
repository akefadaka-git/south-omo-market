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
      if (request.url.path.endsWith('/locations')) {
        return http.Response(jsonEncode([
          {'id': 'loc-koybe', 'name': 'Koybe', 'level': 'locality'},
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
    var authHeaderPresent = false;
    final calls = <String>[];
    final client = MockClient((request) async {
      calls.add('${request.method} ${request.url.path}');
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
        authHeaderPresent = request.headers.entries.any((entry) => entry.key.toLowerCase() == 'authorization' && entry.value == 'Bearer buyer-token');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        sent = body['listing_id'] == 'listing-2' && body['message'] == 'Is this available?';
        return http.Response('{"id":"inquiry-1","status":"open"}', 201);
      }
      return http.Response('Not found', 404);
    });
    await tester.pumpWidget(MaterialApp(home: ListingDetailPage(
      apiBaseUrl: 'https://market.example.test/api/v1', client: client, listingId: 'listing-2',
    )));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('buyer-inquiry-message')), 'Is this available?');
    await tester.tap(find.text('Send inquiry'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('buyer-display-name')), 'Buyer Test');
    await tester.enterText(find.byKey(const Key('buyer-phone')), '+251900000007');
    await tester.enterText(find.byKey(const Key('buyer-password')), 'synthetic-password-123');
    await tester.tap(find.text('Register and continue'));
    await tester.pumpAndSettle();
    expect(registered, isTrue);
    expect(sent, isTrue, reason: 'Requests: ${calls.join(' | ')}');
    expect(authHeaderPresent, isTrue);
    expect(find.text('Your inquiry was sent to the seller.'), findsOneWidget);
    client.close();
  });


  testWidgets('discovery exposes sorting and loads the next listing page', (tester) async {
    final listingRequests = <Uri>[];
    final firstPage = List.generate(50, (index) => {
      'id': 'listing-$index',
      'title': 'Synthetic listing $index',
      'description': 'Synthetic test listing',
      'category_id': 'cat-livestock',
      'price_minor': 10000 + index,
      'location': 'Koybe',
      'images': <Object>[],
    });
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/categories')) {
        return http.Response(jsonEncode([
          {'id': 'cat-livestock', 'name': 'Livestock'},
        ]), 200);
      }
      if (request.url.path.endsWith('/locations')) {
        return http.Response(jsonEncode([
          {'id': 'loc-koybe', 'name': 'Koybe', 'level': 'locality'},
        ]), 200);
      }
      if (request.url.path.endsWith('/listings')) {
        listingRequests.add(request.url);
        final offset = int.tryParse(request.url.queryParameters['offset'] ?? '0') ?? 0;
        return http.Response(jsonEncode(offset == 0 ? firstPage : [
          {
            'id': 'listing-50',
            'title': 'Synthetic listing 50',
            'description': 'Synthetic test listing',
            'category_id': 'cat-livestock',
            'price_minor': 10050,
            'location': 'Koybe',
            'images': <Object>[],
          },
        ]), 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: MarketplaceDiscoveryPage(
      apiBaseUrl: 'https://market.example.test/api/v1', client: client,
    )));
    await tester.pumpAndSettle();
    expect(find.text('Sort listings'), findsOneWidget);
    expect(listingRequests.first.queryParameters['sort'], 'newest');

    await tester.scrollUntilVisible(
      find.text('Load more listings'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.text('Load more listings'));
    await tester.pumpAndSettle();

    expect(listingRequests.last.queryParameters['offset'], '50');
    expect(find.text('Synthetic listing 50'), findsOneWidget);
    client.close();
  });

}


  testWidgets('seller form renders schema fields, validates them and saves attributes', (tester) async {
    var patchBody = <String, dynamic>{};
    var patchCount = 0;
    final schema = [
      {'key': 'breed', 'type': 'text', 'required': true, 'max_length': 80},
      {'key': 'age_months', 'type': 'number', 'required': true, 'min': 0, 'max': 600},
      {'key': 'sex', 'type': 'choice', 'required': true, 'options': ['female', 'male']},
      {'key': 'vaccinated', 'type': 'boolean', 'required': false},
    ];
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/my')) {
        return http.Response(jsonEncode([
          {'id': 'listing-schema', 'category_id': 'cat-cattle', 'title': 'Draft cattle',
           'description': 'Test', 'price_minor': 120000, 'location': 'Koybe',
           'status': 'draft', 'images': [], 'attributes': {}},
        ]), 200);
      }
      if (request.url.path.endsWith('/categories')) {
        return http.Response(jsonEncode([
          {'id': 'cat-root', 'name': 'Livestock', 'parent_id': null,
           'is_leaf': false, 'attributes_schema': []},
          {'id': 'cat-cattle', 'name': 'Cattle', 'parent_id': 'cat-root',
           'is_leaf': true, 'attributes_schema': schema},
        ]), 200);
      }
      if (request.method == 'PATCH' && request.url.path.endsWith('/listings/listing-schema')) {
        patchCount++;
        patchBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({
          'id': 'listing-schema', 'category_id': 'cat-cattle',
          'title': patchBody['title'], 'description': patchBody['description'],
          'price_minor': patchBody['price_minor'], 'location': patchBody['location_label'],
          'status': 'draft', 'images': [], 'attributes': patchBody['attributes'],
        }), 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(home: SellerListingsPage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'synthetic-token', client: client,
    )));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Draft cattle'));
    await tester.pumpAndSettle();

    expect(find.text('Breed *'), findsOneWidget);
    expect(find.text('Age Months *'), findsOneWidget);
    expect(find.text('Sex *'), findsOneWidget);
    expect(find.text('Vaccinated'), findsOneWidget);
    expect(find.text('Livestock'), findsNothing,
      reason: 'Parent categories must not be selectable for listing drafts');

    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();
    expect(patchCount, 0, reason: 'Required category attributes must block saving');
    expect(find.textContaining('required'), findsWidgets);

    await tester.enterText(find.byType(TextFormField).first, 'Local zebu');
    await tester.enterText(find.byType(TextFormField).last, '36');
    await tester.tap(find.byType(DropdownButtonFormField<String>).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('female').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save changes'));
    await tester.pumpAndSettle();

    expect(patchCount, 1);
    expect(patchBody['attributes'], {
      'breed': 'Local zebu',
      'age_months': 36,
      'sex': 'female',
    });
    client.close();
  });
