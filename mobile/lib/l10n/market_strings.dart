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
    'in_review': 'Under review', 'resolved': 'Resolved', 'dismissed': 'Dismissed',
  };
  const amharic = <String, String>{
    'open': 'ክፍት', 'read': 'ተነብቧል', 'closed': 'ተዘግቷል', 'draft': 'ረቂቅ',
    'pending': 'በመጠባበቅ ላይ', 'synced': 'ተመሳስሏል', 'published': 'ታትሟል',
    'pending_review': 'ግምገማ በመጠባበቅ ላይ', 'rejected': 'ውድቅ ተደርጓል',
    'in_review': 'በግምገማ ላይ', 'resolved': 'ተፈትቷል', 'dismissed': 'ውድቅ ተደርጓል',
  };
  final language = Localizations.localeOf(context).languageCode;
  return (language == 'am' ? amharic : english)[status] ?? status;
}

String marketReportReasonLabel(BuildContext context, String reason) {
  const english = <String, String>{
    'fraud': 'Fraud or scam',
    'misleading_information': 'Misleading information',
    'prohibited_item': 'Prohibited item',
    'harassment': 'Harassment',
    'unsafe_activity': 'Unsafe activity',
    'impersonation': 'Impersonation',
    'spam': 'Spam',
    'other': 'Other',
  };
  const amharic = <String, String>{
    'fraud': 'ማጭበርበር',
    'misleading_information': 'አሳሳች መረጃ',
    'prohibited_item': 'የተከለከለ ዕቃ',
    'harassment': 'ማዋከብ',
    'unsafe_activity': 'አደገኛ ተግባር',
    'impersonation': 'ሌላን መምሰል',
    'spam': 'አላስፈላጊ መልዕክት',
    'other': 'ሌላ',
  };
  final language = Localizations.localeOf(context).languageCode;
  return (language == 'am' ? amharic : english)[reason] ?? reason;
}
