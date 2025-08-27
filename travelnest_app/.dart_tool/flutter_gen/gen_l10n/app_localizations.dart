import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen_l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale) : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate = _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates = <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('zh')
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'TravelNest'**
  String get appTitle;

  /// No description provided for @welcomeTitle.
  ///
  /// In en, this message translates to:
  /// **'Welcome to TravelNest'**
  String get welcomeTitle;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Your smart travel companion'**
  String get welcomeSubtitle;

  /// No description provided for @login.
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get login;

  /// No description provided for @signup.
  ///
  /// In en, this message translates to:
  /// **'Sign Up'**
  String get signup;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm Password'**
  String get confirmPassword;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot Password?'**
  String get forgotPassword;

  /// No description provided for @loginWithGoogle.
  ///
  /// In en, this message translates to:
  /// **'Login with Google'**
  String get loginWithGoogle;

  /// No description provided for @loginWithWeChat.
  ///
  /// In en, this message translates to:
  /// **'Login with WeChat'**
  String get loginWithWeChat;

  /// No description provided for @noAccount.
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account?'**
  String get noAccount;

  /// No description provided for @hasAccount.
  ///
  /// In en, this message translates to:
  /// **'Already have an account?'**
  String get hasAccount;

  /// No description provided for @smartPlanning.
  ///
  /// In en, this message translates to:
  /// **'Smart Planning'**
  String get smartPlanning;

  /// No description provided for @editDay.
  ///
  /// In en, this message translates to:
  /// **'Edit Day {day}'**
  String editDay(Object day);

  /// No description provided for @editDayDesc.
  ///
  /// In en, this message translates to:
  /// **'Drag to reorder, tap to delete locations'**
  String get editDayDesc;

  /// No description provided for @editModeEnabled.
  ///
  /// In en, this message translates to:
  /// **'Edit mode enabled'**
  String get editModeEnabled;

  /// No description provided for @addLocation.
  ///
  /// In en, this message translates to:
  /// **'Add Location'**
  String get addLocation;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @noLocations.
  ///
  /// In en, this message translates to:
  /// **'No locations'**
  String get noLocations;

  /// No description provided for @addFirstLocation.
  ///
  /// In en, this message translates to:
  /// **'Click the button below to add your first location'**
  String get addFirstLocation;

  /// No description provided for @deleteConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Confirm Delete'**
  String get deleteConfirmation;

  /// No description provided for @deleteLocationConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete \"{locationName}\"?'**
  String deleteLocationConfirm(Object locationName);

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @locationDeleted.
  ///
  /// In en, this message translates to:
  /// **'Location deleted'**
  String get locationDeleted;

  /// No description provided for @day.
  ///
  /// In en, this message translates to:
  /// **'Day {day}'**
  String day(Object day);

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @view.
  ///
  /// In en, this message translates to:
  /// **'View'**
  String get view;

  /// No description provided for @add.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get add;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @modify.
  ///
  /// In en, this message translates to:
  /// **'Modify'**
  String get modify;

  /// No description provided for @overview.
  ///
  /// In en, this message translates to:
  /// **'Overview'**
  String get overview;

  /// No description provided for @schedule.
  ///
  /// In en, this message translates to:
  /// **'Schedule'**
  String get schedule;

  /// No description provided for @route.
  ///
  /// In en, this message translates to:
  /// **'Route'**
  String get route;

  /// No description provided for @transport.
  ///
  /// In en, this message translates to:
  /// **'Transport'**
  String get transport;

  /// No description provided for @rating.
  ///
  /// In en, this message translates to:
  /// **'Rating'**
  String get rating;

  /// No description provided for @address.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get address;

  /// No description provided for @subway.
  ///
  /// In en, this message translates to:
  /// **'Subway'**
  String get subway;

  /// No description provided for @bus.
  ///
  /// In en, this message translates to:
  /// **'Bus'**
  String get bus;

  /// No description provided for @walk.
  ///
  /// In en, this message translates to:
  /// **'Walk'**
  String get walk;

  /// No description provided for @taxi.
  ///
  /// In en, this message translates to:
  /// **'Taxi'**
  String get taxi;

  /// No description provided for @bike.
  ///
  /// In en, this message translates to:
  /// **'Bike'**
  String get bike;

  /// No description provided for @other.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get other;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @switchLanguage.
  ///
  /// In en, this message translates to:
  /// **'Switch Language'**
  String get switchLanguage;

  /// No description provided for @tokyo5DayTrip.
  ///
  /// In en, this message translates to:
  /// **'Tokyo 5-Day Trip'**
  String get tokyo5DayTrip;

  /// No description provided for @exploreTokyo.
  ///
  /// In en, this message translates to:
  /// **'Explore the modern and traditional charm of Japan\'s capital'**
  String get exploreTokyo;

  /// No description provided for @dateRange.
  ///
  /// In en, this message translates to:
  /// **'March 15-19, 2024'**
  String get dateRange;

  /// No description provided for @days4Nights.
  ///
  /// In en, this message translates to:
  /// **'5 days 4 nights'**
  String get days4Nights;

  /// No description provided for @day1.
  ///
  /// In en, this message translates to:
  /// **'Day 1'**
  String get day1;

  /// No description provided for @day2.
  ///
  /// In en, this message translates to:
  /// **'Day 2'**
  String get day2;

  /// No description provided for @day3.
  ///
  /// In en, this message translates to:
  /// **'Day 3'**
  String get day3;

  /// No description provided for @day4.
  ///
  /// In en, this message translates to:
  /// **'Day 4'**
  String get day4;

  /// No description provided for @day5.
  ///
  /// In en, this message translates to:
  /// **'Day 5'**
  String get day5;

  /// No description provided for @viewDetails.
  ///
  /// In en, this message translates to:
  /// **'View Details'**
  String get viewDetails;

  /// No description provided for @sensojiToSkytree.
  ///
  /// In en, this message translates to:
  /// **'Sensoji → Skytree'**
  String get sensojiToSkytree;

  /// No description provided for @meijiShrineToShibuya.
  ///
  /// In en, this message translates to:
  /// **'Meiji Shrine → Shibuya'**
  String get meijiShrineToShibuya;

  /// No description provided for @uenoParkToAkihabara.
  ///
  /// In en, this message translates to:
  /// **'Ueno Park → Akihabara'**
  String get uenoParkToAkihabara;

  /// No description provided for @odaibaToGinza.
  ///
  /// In en, this message translates to:
  /// **'Odaiba → Ginza'**
  String get odaibaToGinza;

  /// No description provided for @shinjukuToIkebukuro.
  ///
  /// In en, this message translates to:
  /// **'Shinjuku → Ikebukuro'**
  String get shinjukuToIkebukuro;

  /// No description provided for @sensoji.
  ///
  /// In en, this message translates to:
  /// **'Sensoji Temple'**
  String get sensoji;

  /// No description provided for @tokyoSkytree.
  ///
  /// In en, this message translates to:
  /// **'Tokyo Skytree'**
  String get tokyoSkytree;

  /// No description provided for @meijiShrine.
  ///
  /// In en, this message translates to:
  /// **'Meiji Shrine'**
  String get meijiShrine;

  /// No description provided for @asakusaAddress.
  ///
  /// In en, this message translates to:
  /// **'2-3-1 Asakusa, Taito City, Tokyo'**
  String get asakusaAddress;

  /// No description provided for @skytreeAddress.
  ///
  /// In en, this message translates to:
  /// **'1-1-2 Oshiage, Sumida City, Tokyo'**
  String get skytreeAddress;

  /// No description provided for @meijiShrineAddress.
  ///
  /// In en, this message translates to:
  /// **'1-1 Yoyogikamizonocho, Shibuya City, Tokyo'**
  String get meijiShrineAddress;

  /// No description provided for @asakusaLineAsakusaStation.
  ///
  /// In en, this message translates to:
  /// **'Asakusa Line, Asakusa Station, 5 minutes walk'**
  String get asakusaLineAsakusaStation;

  /// No description provided for @asakusaLineOshiageStation.
  ///
  /// In en, this message translates to:
  /// **'Asakusa Line, Oshiage Station, 3 minutes walk'**
  String get asakusaLineOshiageStation;

  /// No description provided for @jrYamanoteLineHarajukuStation.
  ///
  /// In en, this message translates to:
  /// **'JR Yamanote Line, Harajuku Station, 5 minutes walk'**
  String get jrYamanoteLineHarajukuStation;

  /// No description provided for @startExploring.
  ///
  /// In en, this message translates to:
  /// **'Start Exploring'**
  String get startExploring;

  /// No description provided for @loginAccount.
  ///
  /// In en, this message translates to:
  /// **'Login Account'**
  String get loginAccount;

  /// No description provided for @copyright.
  ///
  /// In en, this message translates to:
  /// **'© 2024 TravelNest. All rights reserved.'**
  String get copyright;

  /// No description provided for @smartPlanningEasyTravel.
  ///
  /// In en, this message translates to:
  /// **'Smart Planning, Easy Travel'**
  String get smartPlanningEasyTravel;

  /// No description provided for @welcomeBack.
  ///
  /// In en, this message translates to:
  /// **'Welcome Back'**
  String get welcomeBack;

  /// No description provided for @loginToContinue.
  ///
  /// In en, this message translates to:
  /// **'Login to your account to continue exploring'**
  String get loginToContinue;

  /// No description provided for @google.
  ///
  /// In en, this message translates to:
  /// **'Google'**
  String get google;

  /// No description provided for @wechat.
  ///
  /// In en, this message translates to:
  /// **'WeChat'**
  String get wechat;

  /// No description provided for @orLoginWithEmail.
  ///
  /// In en, this message translates to:
  /// **'Or login with email'**
  String get orLoginWithEmail;

  /// No description provided for @emailAddress.
  ///
  /// In en, this message translates to:
  /// **'Email Address'**
  String get emailAddress;

  /// No description provided for @enterYourEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter your email'**
  String get enterYourEmail;

  /// No description provided for @enterYourPassword.
  ///
  /// In en, this message translates to:
  /// **'Enter your password'**
  String get enterYourPassword;

  /// No description provided for @enterEmailAddress.
  ///
  /// In en, this message translates to:
  /// **'Please enter email address'**
  String get enterEmailAddress;

  /// No description provided for @enterValidEmail.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address'**
  String get enterValidEmail;

  /// No description provided for @enterPassword.
  ///
  /// In en, this message translates to:
  /// **'Please enter password'**
  String get enterPassword;

  /// No description provided for @passwordAtLeast6.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 6 characters'**
  String get passwordAtLeast6;

  /// No description provided for @signUpNow.
  ///
  /// In en, this message translates to:
  /// **'Sign up now'**
  String get signUpNow;

  /// No description provided for @map.
  ///
  /// In en, this message translates to:
  /// **'Map'**
  String get map;

  /// No description provided for @mapComingSoon.
  ///
  /// In en, this message translates to:
  /// **'Map Coming Soon'**
  String get mapComingSoon;

  /// No description provided for @mapDescription.
  ///
  /// In en, this message translates to:
  /// **'Interactive map view will be available here for viewing and planning your travel route'**
  String get mapDescription;

  /// No description provided for @akihabara.
  ///
  /// In en, this message translates to:
  /// **'Akihabara'**
  String get akihabara;

  /// No description provided for @akihabaraAddress.
  ///
  /// In en, this message translates to:
  /// **'Soto-Kanda, Chiyoda City, Tokyo'**
  String get akihabaraAddress;

  /// No description provided for @jrYamanoteLineAkihabaraStation.
  ///
  /// In en, this message translates to:
  /// **'JR Yamanote Line, Akihabara Station'**
  String get jrYamanoteLineAkihabaraStation;

  /// No description provided for @shibuyaCrossing.
  ///
  /// In en, this message translates to:
  /// **'Shibuya Crossing'**
  String get shibuyaCrossing;

  /// No description provided for @shibuyaAddress.
  ///
  /// In en, this message translates to:
  /// **'Shibuya, Shibuya City, Tokyo'**
  String get shibuyaAddress;

  /// No description provided for @walkFromMeijiShrine.
  ///
  /// In en, this message translates to:
  /// **'15 minutes walk from Meiji Shrine'**
  String get walkFromMeijiShrine;

  /// No description provided for @locations.
  ///
  /// In en, this message translates to:
  /// **'locations'**
  String get locations;

  /// No description provided for @daySchedule.
  ///
  /// In en, this message translates to:
  /// **'Day Schedule'**
  String get daySchedule;
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>['en', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {


  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en': return AppLocalizationsEn();
    case 'zh': return AppLocalizationsZh();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.'
  );
}
