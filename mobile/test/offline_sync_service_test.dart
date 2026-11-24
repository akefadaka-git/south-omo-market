import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/data/local_draft_store.dart';
import 'package:south_omo_market/data/offline_sync_service.dart';

class FakeDraftStore extends LocalDraftStore {
  final drafts = <Map<String, Object?>>[
    {
      'id': 'local-draft-uuid',
      'client_sync_id': 'local-draft-uuid',
      'category_id': '00000000-0000-4000-8000-000000000001',
      'title': 'Synthetic offline goats',
      'description': 'Queued test draft',
      'attributes_json': jsonEncode({'breed': 'Local', 'age_months': 24, 'sex': 'female'}),
      'price_minor': 450000,
      'location_label': 'Koybe',
    },
  ];
  final images = <Map<String, Object?>>[];
  String? syncedId;
  String? failure;
  String? uploadedImageId;

  @override
  Future<List<Map<String, Object?>>> pendingDrafts() async => drafts;

  @override
  Future<List<Map<String, Object?>>> pendingImages(String draftId) async => images;

  @override
  Future<void> markDraftSynced(String id, String serverListingId) async {
    syncedId = serverListingId;
  }

  @override
  Future<void> markDraftFailed(String id, String message) async {
    failure = message;
  }

  @override
  Future<void> markImageUploaded(String id, String serverImageId) async {
    uploadedImageId = serverImageId;
  }
}

void main() {
  test('offline sync creates a server draft using its stable idempotency key', () async {
    final store = FakeDraftStore();
    var requests = 0;
    final client = MockClient((request) async {
      requests++;
      expect(request.url.path, '/api/v1/listings/sync');
      expect(request.headers['Authorization'], 'Bearer synthetic-token');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['attributes'], {'breed': 'Local', 'age_months': 24, 'sex': 'female'});
      return http.Response(
        '{"id":"server-listing-123","status":"draft","idempotent":false}',
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final result = await OfflineSyncService(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'synthetic-token',
      store: store,
      client: client,
    ).syncPending();

    expect(requests, 1);
    expect(result.synced, 1);
    expect(result.failed, 0);
    expect(store.syncedId, 'server-listing-123');
    expect(store.failure, isNull);
    client.close();
  });

  test('offline sync keeps a failed draft retryable', () async {
    final store = FakeDraftStore();
    final client = MockClient((request) async =>
        http.Response('temporarily unavailable', 503));

    final result = await OfflineSyncService(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'synthetic-token',
      store: store,
      client: client,
    ).syncPending();

    expect(result.synced, 0);
    expect(result.failed, 1);
    expect(store.syncedId, isNull);
    expect(store.failure, contains('503'));
    client.close();
  });

  test('offline sync uploads a queued image with its stable client image ID', () async {
    final directory = await Directory.systemTemp.createTemp('market-sync-test');
    final imageFile = File('${directory.path}/synthetic.jpg');
    await imageFile.writeAsBytes('synthetic image bytes'.codeUnits);
    final store = FakeDraftStore()
      ..images.add({
        'id': 'stable-image-uuid',
        'local_path': imageFile.path,
      });
    var uploadRequested = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/listings/sync')) {
        return http.Response(
          '{"id":"server-listing-456","status":"draft","idempotent":false}',
          200,
        );
      }
      uploadRequested = request.url.path.endsWith('/listings/server-listing-456/images');
      return http.Response(
        '{"id":"server-image-789","url":"/image.jpg"}',
        201,
      );
    });

    final result = await OfflineSyncService(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'synthetic-token',
      store: store,
      client: client,
    ).syncPending();

    expect(store.failure, isNull, reason: store.failure);
    expect(uploadRequested, isTrue);
    expect(result.synced, 1);
    expect(result.failed, 0);
    expect(store.uploadedImageId, 'server-image-789');
    expect(store.syncedId, 'server-listing-456');
    await directory.delete(recursive: true);
    client.close();
  });
}
