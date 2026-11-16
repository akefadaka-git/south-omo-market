import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class LocalDraftStore {
  static const _databaseName = 'south_omo_market.db';
  static const _databaseVersion = 1;
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
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price_minor INTEGER NOT NULL DEFAULT 0,
            location_label TEXT NOT NULL,
            sync_state TEXT NOT NULL DEFAULT 'pending',
            updated_at TEXT NOT NULL
          )
        ''');
      },
    );
    return _database!;
  }

  Future<void> saveDraft(Map<String, Object?> draft) async {
    final db = await database;
    await db.insert('listing_drafts', draft,
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, Object?>>> pendingDrafts() async {
    final db = await database;
    return db.query('listing_drafts',
        where: 'sync_state = ?', whereArgs: ['pending'], orderBy: 'updated_at ASC');
  }
}
