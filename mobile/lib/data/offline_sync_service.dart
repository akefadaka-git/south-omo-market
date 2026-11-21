import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'local_draft_store.dart';

class SyncSummary {
  const SyncSummary({required this.synced, required this.failed});
  final int synced;
  final int failed;
}

class OfflineSyncService {
  OfflineSyncService({
    required this.apiBaseUrl,
    required this.accessToken,
    required this.store,
    required this.client,
  });

  final String apiBaseUrl;
  final String accessToken;
  final LocalDraftStore store;
  final http.Client client;

  Map<String, String> get _headers => {
    'Authorization': 'Bearer $accessToken',
    'Content-Type': 'application/json',
  };

  Future<SyncSummary> syncPending() async {
    var synced = 0;
    var failed = 0;
    final drafts = await store.pendingDrafts();
    for (final draft in drafts) {
      final id = draft['id'] as String;
      try {
        final response = await client.post(
          Uri.parse('${apiBaseUrl.replaceFirst(RegExp(r'/+$'), '')}/listings/sync'),
          headers: _headers,
          body: jsonEncode({
            'client_sync_id': draft['client_sync_id'],
            'category_id': draft['category_id'],
            'title': draft['title'],
            'description': draft['description'] ?? '',
            'attributes': jsonDecode((draft['attributes_json'] as String?) ?? '{}'),
            'price_minor': draft['price_minor'],
            'location_label': draft['location_label'],
          }),
        );
        if (response.statusCode != 200) {
          throw HttpException('Draft sync failed (${response.statusCode})');
        }
        final result = jsonDecode(response.body) as Map<String, dynamic>;
        final serverListingId = result['id'] as String;
        final images = await store.pendingImages(id);
        for (final image in images) {
          final path = image['local_path'] as String;
          if (!await File(path).exists()) {
            throw const FileSystemException('A queued listing image is no longer available');
          }
          final request = http.MultipartRequest(
            'POST',
            Uri.parse(
              '${apiBaseUrl.replaceFirst(RegExp(r'/+$'), '')}/listings/$serverListingId/images',
            ),
          )
            ..headers['Authorization'] = 'Bearer $accessToken'
            ..fields['client_image_id'] = image['id'] as String
            ..files.add(await http.MultipartFile.fromPath('file', path));
          final streamed = await client.send(request);
          final uploadResponse = await http.Response.fromStream(streamed);
          if (uploadResponse.statusCode != 201) {
            throw HttpException('Image upload failed (${uploadResponse.statusCode})');
          }
          final uploaded = jsonDecode(uploadResponse.body) as Map<String, dynamic>;
          await store.markImageUploaded(image['id'] as String, uploaded['id'] as String);
        }
        await store.markDraftSynced(id, serverListingId);
        synced++;
      } catch (error) {
        await store.markDraftFailed(id, error.toString());
        failed++;
      }
    }
    return SyncSummary(synced: synced, failed: failed);
  }
}
