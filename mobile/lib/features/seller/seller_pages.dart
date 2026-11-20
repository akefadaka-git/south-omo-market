import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../../data/local_draft_store.dart';
import '../../data/offline_sync_service.dart';
import '../../marketplace_pages.dart';
import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';
