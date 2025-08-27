// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'TravelNest';

  @override
  String get welcomeTitle => 'Welcome to TravelNest';

  @override
  String get welcomeSubtitle => 'Your smart travel companion';

  @override
  String get login => 'Login';

  @override
  String get signup => 'Sign Up';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm Password';

  @override
  String get forgotPassword => 'Forgot Password?';

  @override
  String get loginWithGoogle => 'Login with Google';

  @override
  String get loginWithWeChat => 'Login with WeChat';

  @override
  String get noAccount => 'Don\'t have an account?';

  @override
  String get hasAccount => 'Already have an account?';

  @override
  String get smartPlanning => 'Smart Planning';

  @override
  String editDay(Object day) {
    return 'Edit Day $day';
  }

  @override
  String get editDayDesc => 'Drag to reorder, tap to delete locations';

  @override
  String get editModeEnabled => 'Edit mode enabled';

  @override
  String get addLocation => 'Add Location';

  @override
  String get done => 'Done';

  @override
  String get noLocations => 'No locations';

  @override
  String get addFirstLocation => 'Click the button below to add your first location';

  @override
  String get deleteConfirmation => 'Confirm Delete';

  @override
  String deleteLocationConfirm(Object locationName) {
    return 'Are you sure you want to delete \"$locationName\"?';
  }

  @override
  String get cancel => 'Cancel';

  @override
  String get delete => 'Delete';

  @override
  String get locationDeleted => 'Location deleted';

  @override
  String day(Object day) {
    return 'Day $day';
  }

  @override
  String get edit => 'Edit';

  @override
  String get view => 'View';

  @override
  String get add => 'Add';

  @override
  String get back => 'Back';

  @override
  String get save => 'Save';

  @override
  String get modify => 'Modify';

  @override
  String get overview => 'Overview';

  @override
  String get schedule => 'Schedule';

  @override
  String get route => 'Route';

  @override
  String get transport => 'Transport';

  @override
  String get rating => 'Rating';

  @override
  String get address => 'Address';

  @override
  String get subway => 'Subway';

  @override
  String get bus => 'Bus';

  @override
  String get walk => 'Walk';

  @override
  String get taxi => 'Taxi';

  @override
  String get bike => 'Bike';

  @override
  String get other => 'Other';

  @override
  String get language => 'Language';

  @override
  String get switchLanguage => 'Switch Language';

  @override
  String get tokyo5DayTrip => 'Tokyo 5-Day Trip';

  @override
  String get exploreTokyo => 'Explore the modern and traditional charm of Japan\'s capital';

  @override
  String get dateRange => 'March 15-19, 2024';

  @override
  String get days4Nights => '5 days 4 nights';

  @override
  String get day1 => 'Day 1';

  @override
  String get day2 => 'Day 2';

  @override
  String get day3 => 'Day 3';

  @override
  String get day4 => 'Day 4';

  @override
  String get day5 => 'Day 5';

  @override
  String get viewDetails => 'View Details';

  @override
  String get sensojiToSkytree => 'Sensoji → Skytree';

  @override
  String get meijiShrineToShibuya => 'Meiji Shrine → Shibuya';

  @override
  String get uenoParkToAkihabara => 'Ueno Park → Akihabara';

  @override
  String get odaibaToGinza => 'Odaiba → Ginza';

  @override
  String get shinjukuToIkebukuro => 'Shinjuku → Ikebukuro';

  @override
  String get sensoji => 'Sensoji Temple';

  @override
  String get tokyoSkytree => 'Tokyo Skytree';

  @override
  String get meijiShrine => 'Meiji Shrine';

  @override
  String get asakusaAddress => '2-3-1 Asakusa, Taito City, Tokyo';

  @override
  String get skytreeAddress => '1-1-2 Oshiage, Sumida City, Tokyo';

  @override
  String get meijiShrineAddress => '1-1 Yoyogikamizonocho, Shibuya City, Tokyo';

  @override
  String get asakusaLineAsakusaStation => 'Asakusa Line, Asakusa Station, 5 minutes walk';

  @override
  String get asakusaLineOshiageStation => 'Asakusa Line, Oshiage Station, 3 minutes walk';

  @override
  String get jrYamanoteLineHarajukuStation => 'JR Yamanote Line, Harajuku Station, 5 minutes walk';

  @override
  String get startExploring => 'Start Exploring';

  @override
  String get loginAccount => 'Login Account';

  @override
  String get copyright => '© 2024 TravelNest. All rights reserved.';

  @override
  String get smartPlanningEasyTravel => 'Smart Planning, Easy Travel';

  @override
  String get welcomeBack => 'Welcome Back';

  @override
  String get loginToContinue => 'Login to your account to continue exploring';

  @override
  String get google => 'Google';

  @override
  String get wechat => 'WeChat';

  @override
  String get orLoginWithEmail => 'Or login with email';

  @override
  String get emailAddress => 'Email Address';

  @override
  String get enterYourEmail => 'Enter your email';

  @override
  String get enterYourPassword => 'Enter your password';

  @override
  String get enterEmailAddress => 'Please enter email address';

  @override
  String get enterValidEmail => 'Please enter a valid email address';

  @override
  String get enterPassword => 'Please enter password';

  @override
  String get passwordAtLeast6 => 'Password must be at least 6 characters';

  @override
  String get signUpNow => 'Sign up now';

  @override
  String get map => 'Map';

  @override
  String get mapComingSoon => 'Map Coming Soon';

  @override
  String get mapDescription => 'Interactive map view will be available here for viewing and planning your travel route';

  @override
  String get akihabara => 'Akihabara';

  @override
  String get akihabaraAddress => 'Soto-Kanda, Chiyoda City, Tokyo';

  @override
  String get jrYamanoteLineAkihabaraStation => 'JR Yamanote Line, Akihabara Station';

  @override
  String get shibuyaCrossing => 'Shibuya Crossing';

  @override
  String get shibuyaAddress => 'Shibuya, Shibuya City, Tokyo';

  @override
  String get walkFromMeijiShrine => '15 minutes walk from Meiji Shrine';

  @override
  String get locations => 'locations';

  @override
  String get daySchedule => 'Day Schedule';
}
