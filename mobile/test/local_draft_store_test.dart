import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite/sqflite.dart' as sqflite;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:south_omo_market/data/local_draft_store.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    sqflite.databaseFactory = databaseFactoryFfi;
  });

  test('local draft and photo queue persist state transitions', () async {
    final directory = await Directory.systemTemp.createTemp('market-drafts');
    final store = LocalDraftStore(databasePath: '${directory.path}/drafts.db');
    final id = '7a1f94b2-66c4-4e4c-95a1-123456789abc';
    await store.saveDraft({
      'id': id,
      'client_sync_id': id,
      'category_id': '00000000-0000-4000-8000-000000000001',
      'title': 'Synthetic offline cattle',
      'description': '',
      'attributes_json': '{"breed":"Local","age_months":24,"sex":"female"}',
      'price_minor': 123450,
      'location_label': 'Koybe',
      'sync_state': 'pending',
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    });
    final savedDraft = (await store.pendingDrafts()).single;
    expect(savedDraft['id'], id);
    expect(savedDraft['attributes_json'], '{"breed":"Local","age_months":24,"sex":"female"}');

    await store.addImage(
      id: 'f09a5c0d-54e2-43d6-a11f-123456789abc',
      draftId: id,
      localPath: '/private/synthetic.jpg',
    );
    expect((await store.pendingImages(id)).length, 1);
    await store.markImageUploaded(
      'f09a5c0d-54e2-43d6-a11f-123456789abc',
      'server-image-id',
    );
    expect((await store.pendingImages(id)), isEmpty);
    expect((await store.allImages(id)).single['uploaded'], 1);

    await store.markDraftSynced(id, 'server-listing-id');
    expect(await store.pendingDrafts(), isEmpty);
    expect((await store.allDrafts()).single['server_listing_id'], 'server-listing-id');
    await store.close();
    await directory.delete(recursive: true);
  });

  test('version-one drafts are retained and receive stable sync IDs on upgrade', () async {
    final directory = await Directory.systemTemp.createTemp('market-draft-upgrade');
    final path = '${directory.path}/legacy.db';
    final legacy = await sqflite.openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE listing_drafts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price_minor INTEGER NOT NULL DEFAULT 0,
            location_label TEXT NOT NULL,
            sync_state TEXT NOT NULL DEFAULT 'pending',
            updated_at TEXT NOT NULL
          )
        ''');
        await db.insert('listing_drafts', {
          'id': 'legacy-local-id',
          'title': 'Legacy draft',
          'description': '',
          'price_minor': 10000,
          'location_label': 'Jinka',
          'sync_state': 'pending',
          'updated_at': '2026-01-01T00:00:00Z',
        });
      },
    );
    await legacy.close();

    final store = LocalDraftStore(databasePath: path);
    final retained = (await store.allDrafts()).single;
    expect(retained['title'], 'Legacy draft');
    expect(retained['client_sync_id'], matches(RegExp(
      r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    )));
    expect(retained['category_id'], isNull);
    expect(await store.pendingDrafts(), isEmpty);

    await store.saveDraft({
      ...retained,
      'category_id': '00000000-0000-4000-8000-000000000001',
      'sync_state': 'pending',
    });
    expect((await store.pendingDrafts()).single['id'], 'legacy-local-id');
    await store.close();
    await directory.delete(recursive: true);
  });
}
