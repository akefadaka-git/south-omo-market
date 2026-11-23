import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

class LocalDraftStore {
  static const _databaseName = 'south_omo_market.db';
  static const _databaseVersion = 5;
  LocalDraftStore({String? databasePath}) : _databasePath = databasePath;

  final String? _databasePath;
  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    final root = await getDatabasesPath();
    _database = await openDatabase(
      _databasePath ?? p.join(root, _databaseName),
      version: _databaseVersion,
      onConfigure: (db) async {
        await db.execute('PRAGMA foreign_keys = ON');
      },
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE listing_drafts (
            id TEXT PRIMARY KEY,
            client_sync_id TEXT NOT NULL UNIQUE,
            category_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            attributes_json TEXT NOT NULL DEFAULT '{}',
            price_minor INTEGER NOT NULL DEFAULT 0,
            location_label TEXT NOT NULL,
            server_listing_id TEXT,
            sync_state TEXT NOT NULL DEFAULT 'pending',
            last_error TEXT,
            updated_at TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE listing_draft_images (
            id TEXT PRIMARY KEY,
            draft_id TEXT NOT NULL,
            local_path TEXT NOT NULL,
            server_image_id TEXT,
            uploaded INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(draft_id) REFERENCES listing_drafts(id) ON DELETE CASCADE
          )
        ''');
        await db.execute(
          'CREATE INDEX ix_listing_draft_images_draft_id ON listing_draft_images(draft_id)',
        );
        await db.execute('''
          CREATE TABLE category_catalogue_cache (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE market_schedule_cache (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
          )
        ''');
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 5) {
          await db.execute('''
            CREATE TABLE market_schedule_cache (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
        }
        if (oldVersion < 2) {
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN client_sync_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN category_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN server_listing_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN last_error TEXT");
          final legacyDrafts = await db.query(
            'listing_drafts',
            columns: ['id'],
            where: 'client_sync_id IS NULL',
          );
          const uuid = Uuid();
          for (final draft in legacyDrafts) {
            await db.update(
              'listing_drafts',
              {'client_sync_id': uuid.v4()},
              where: 'id = ?',
              whereArgs: [draft['id']],
            );
          }
          await db.execute('''
            CREATE TABLE listing_draft_images (
              id TEXT PRIMARY KEY,
              draft_id TEXT NOT NULL,
              local_path TEXT NOT NULL,
              server_image_id TEXT,
              uploaded INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY(draft_id) REFERENCES listing_drafts(id) ON DELETE CASCADE
            )
          ''');
          await db.execute(
            'CREATE INDEX ix_listing_draft_images_draft_id ON listing_draft_images(draft_id)',
          );
        }
        if (oldVersion < 3) {
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN attributes_json TEXT NOT NULL DEFAULT '{}'");
        }
        if (oldVersion < 4) {
          await db.execute('''
            CREATE TABLE category_catalogue_cache (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
        }
      },
    );
    return _database!;
  }


  Future<void> saveCategoryCatalogue(List<Map<String, dynamic>> categories) async {
    final db = await database;
    await db.insert('category_catalogue_cache', {
      'id': 1,
      'payload': jsonEncode(categories),
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> cachedCategoryCatalogue() async {
    final db = await database;
    final rows = await db.query('category_catalogue_cache', where: 'id = 1', limit: 1);
    if (rows.isEmpty) return [];
    final decoded = jsonDecode(rows.single['payload'] as String) as List<dynamic>;
    return decoded.cast<Map<String, dynamic>>();
  }

  Future<void> saveMarketSchedule(Map<String, dynamic> schedule) async {
    final db = await database;
    await db.insert('market_schedule_cache', {
      'id': 1,
      'payload': jsonEncode(schedule),
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<Map<String, dynamic>?> cachedMarketSchedule() async {
    final db = await database;
    final rows = await db.query('market_schedule_cache', where: 'id = 1', limit: 1);
    if (rows.isEmpty) return null;
    final payload = jsonDecode(rows.single['payload'] as String) as Map<String, dynamic>;
    payload['cached_at'] = rows.single['updated_at'];
    return payload;
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }

  Future<void> saveDraft(Map<String, Object?> draft) async {
    final db = await database;
    final id = draft['id'];
    if (id is! String || id.isEmpty) {
      throw ArgumentError.value(id, 'id', 'A stable draft UUID is required');
    }
    final updated = await db.update('listing_drafts', draft, where: 'id = ?', whereArgs: [id]);
    if (updated == 0) await db.insert('listing_drafts', draft);
  }

  Future<List<Map<String, Object?>>> pendingDrafts() async {
    final db = await database;
    return db.query(
      'listing_drafts',
      where: "sync_state IN ('pending', 'failed') AND category_id IS NOT NULL",
      orderBy: 'updated_at ASC',
    );
  }

  Future<List<Map<String, Object?>>> allDrafts() async {
    final db = await database;
    return db.query('listing_drafts', orderBy: 'updated_at DESC');
  }

  Future<void> addImage({
    required String id,
    required String draftId,
    required String localPath,
  }) async {
    final db = await database;
    await db.insert('listing_draft_images', {
      'id': id, 'draft_id': draftId, 'local_path': localPath, 'uploaded': 0,
    });
  }

  Future<List<Map<String, Object?>>> pendingImages(String draftId) async {
    final db = await database;
    return db.query(
      'listing_draft_images',
      where: 'draft_id = ? AND uploaded = 0',
      whereArgs: [draftId],
      orderBy: 'rowid ASC',
    );
  }

  Future<List<Map<String, Object?>>> allImages(String draftId) async {
    final db = await database;
    return db.query(
      'listing_draft_images',
      where: 'draft_id = ?',
      whereArgs: [draftId],
      orderBy: 'rowid ASC',
    );
  }

  Future<void> markImageUploaded(String id, String serverImageId) async {
    final db = await database;
    await db.update('listing_draft_images', {
      'uploaded': 1, 'server_image_id': serverImageId,
    }, where: 'id = ?', whereArgs: [id]);
  }

  Future<void> markDraftSynced(String id, String serverListingId) async {
    final db = await database;
    await db.update('listing_drafts', {
      'server_listing_id': serverListingId,
      'sync_state': 'synced',
      'last_error': null,
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    }, where: 'id = ?', whereArgs: [id]);
  }

  Future<void> markDraftFailed(String id, String message) async {
    final db = await database;
    await db.update('listing_drafts', {
      'sync_state': 'failed',
      'last_error': message,
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    }, where: 'id = ?', whereArgs: [id]);
  }
}
