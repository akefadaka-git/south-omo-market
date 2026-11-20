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
