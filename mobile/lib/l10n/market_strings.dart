import 'package:flutter/widgets.dart';

String marketString(
  BuildContext context, {
  required String en,
  required String am,
  required String mdy,
}) {
  switch (Localizations.localeOf(context).languageCode) {
    case 'am':
      return am;
    case 'mdy':
      return mdy.isEmpty ? en : mdy;
    default:
      return en;
  }
}

String marketStatusLabel(BuildContext context, String status) {
  const english = <String, String>{
    'open': 'Open', 'read': 'Read', 'closed': 'Closed', 'draft': 'Draft',
    'pending': 'Pending', 'synced': 'Synced', 'published': 'Published',
    'pending_review': 'Pending review', 'rejected': 'Rejected',
  };
  const amharic = <String, String>{
    'open': 'ክፍት', 'read': 'ተነብቧል', 'closed': 'ተዘግቷል', 'draft': 'ረቂቅ',
    'pending': 'በመጠባበቅ ላይ', 'synced': 'ተመሳስሏል', 'published': 'ታትሟል',
    'pending_review': 'ግምገማ በመጠባበቅ ላይ', 'rejected': 'ውድቅ ተደርጓል',
  };
  final language = Localizations.localeOf(context).languageCode;
  return (language == 'am' ? amharic : english)[status] ?? status;
}
