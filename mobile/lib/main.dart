import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

void main() => runApp(const SouthOmoMarketApp());

class SouthOmoMarketApp extends StatelessWidget {
  const SouthOmoMarketApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'South Omo Market',
        debugShowCheckedModeBanner: false,
        supportedLocales: const [Locale('am'), Locale('en'), Locale('mdy')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF356859)),
          useMaterial3: true,
        ),
        home: const MarketplaceHomePage(),
      );
}

class MarketplaceHomePage extends StatelessWidget {
  const MarketplaceHomePage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('South Omo Market')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Discover local goods and services.\n'
              'Language content is subject to community review.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
}
