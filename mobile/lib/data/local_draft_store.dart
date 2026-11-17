import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class LocalDraftStore {
  static const _databaseName = 'south_omo_market.db';
  static const _databaseVersion = 2;
  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    final root = await getDatabasesPath();
    _database = await openDatabase(
      p.join(root, _databaseName),
      version: _databaseVersion,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE listing_drafts (
            id TEXT PRIMARY KEY,
            client_sync_id TEXT NOT NULL UNIQUE,
            category_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
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
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN client_sync_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN category_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN server_listing_id TEXT");
          await db.execute("ALTER TABLE listing_drafts ADD COLUMN last_error TEXT");
          await db.execute(
            "UPDATE listing_drafts SET client_sync_id = id WHERE client_sync_id IS NULL",
          );
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
      },
    );
    return _database!;
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
