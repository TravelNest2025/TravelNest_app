// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appTitle => '旅行巢';

  @override
  String get welcomeTitle => '欢迎使用旅行巢';

  @override
  String get welcomeSubtitle => '您的智能旅行伙伴';

  @override
  String get login => '登录';

  @override
  String get signup => '注册';

  @override
  String get email => '邮箱';

  @override
  String get password => '密码';

  @override
  String get confirmPassword => '确认密码';

  @override
  String get forgotPassword => '忘记密码？';

  @override
  String get loginWithGoogle => '使用谷歌登录';

  @override
  String get loginWithWeChat => '使用微信登录';

  @override
  String get noAccount => '还没有账户？';

  @override
  String get hasAccount => '已有账户？';

  @override
  String get smartPlanning => '智能规划';

  @override
  String editDay(Object day) {
    return '编辑第$day天';
  }

  @override
  String get editDayDesc => '拖拽重新排序，点击删除地点';

  @override
  String get editModeEnabled => '编辑模式已开启';

  @override
  String get addLocation => '添加地点';

  @override
  String get done => '完成';

  @override
  String get noLocations => '暂无地点';

  @override
  String get addFirstLocation => '点击下方按钮添加第一个地点';

  @override
  String get deleteConfirmation => '确认删除';

  @override
  String deleteLocationConfirm(Object locationName) {
    return '确定要删除\"$locationName\"吗？';
  }

  @override
  String get cancel => '取消';

  @override
  String get delete => '删除';

  @override
  String get locationDeleted => '地点已删除';

  @override
  String day(Object day) {
    return '第$day天';
  }

  @override
  String get edit => '编辑';

  @override
  String get view => '查看';

  @override
  String get add => '添加';

  @override
  String get back => '返回';

  @override
  String get save => '保存';

  @override
  String get modify => '修改';

  @override
  String get overview => '概览';

  @override
  String get schedule => '日程';

  @override
  String get route => '路线';

  @override
  String get transport => '交通';

  @override
  String get rating => '评分';

  @override
  String get address => '地址';

  @override
  String get subway => '地铁';

  @override
  String get bus => '公交';

  @override
  String get walk => '步行';

  @override
  String get taxi => '出租车';

  @override
  String get bike => '自行车';

  @override
  String get other => '其他';

  @override
  String get language => '语言';

  @override
  String get switchLanguage => '切换语言';

  @override
  String get tokyo5DayTrip => '东京5日游';

  @override
  String get exploreTokyo => '探索日本首都的现代与传统魅力';

  @override
  String get dateRange => '2024年3月15日 - 3月19日';

  @override
  String get days4Nights => '5天4晚';

  @override
  String get day1 => '第1天';

  @override
  String get day2 => '第2天';

  @override
  String get day3 => '第3天';

  @override
  String get day4 => '第4天';

  @override
  String get day5 => '第5天';

  @override
  String get viewDetails => '查看详情';

  @override
  String get sensojiToSkytree => '浅草寺 → 晴空塔';

  @override
  String get meijiShrineToShibuya => '明治神宫 → 涩谷';

  @override
  String get uenoParkToAkihabara => '上野公园 → 秋叶原';

  @override
  String get odaibaToGinza => '台场 → 银座';

  @override
  String get shinjukuToIkebukuro => '新宿 → 池袋';

  @override
  String get sensoji => '浅草寺';

  @override
  String get tokyoSkytree => '东京晴空塔';

  @override
  String get meijiShrine => '明治神宫';

  @override
  String get asakusaAddress => '东京都台东区浅草2-3-1';

  @override
  String get skytreeAddress => '东京都墨田区押上1-1-2';

  @override
  String get meijiShrineAddress => '东京都涩谷区代代木神园町1-1';

  @override
  String get asakusaLineAsakusaStation => '浅草线浅草站步行5分钟';

  @override
  String get asakusaLineOshiageStation => '浅草线押上站步行3分钟';

  @override
  String get jrYamanoteLineHarajukuStation => 'JR山手线原宿站步行5分钟';

  @override
  String get startExploring => '开始探索';

  @override
  String get loginAccount => '登录账户';

  @override
  String get copyright => '© 2024 TravelNest. 保留所有权利。';

  @override
  String get smartPlanningEasyTravel => '智能规划，轻松旅行';

  @override
  String get welcomeBack => '欢迎回来';

  @override
  String get loginToContinue => '登录您的账户继续探索';

  @override
  String get google => '谷歌';

  @override
  String get wechat => '微信';

  @override
  String get orLoginWithEmail => '或使用邮箱登录';

  @override
  String get emailAddress => '邮箱地址';

  @override
  String get enterYourEmail => '请输入您的邮箱';

  @override
  String get enterYourPassword => '请输入您的密码';

  @override
  String get enterEmailAddress => '请输入邮箱地址';

  @override
  String get enterValidEmail => '请输入有效的邮箱地址';

  @override
  String get enterPassword => '请输入密码';

  @override
  String get passwordAtLeast6 => '密码至少6位';

  @override
  String get signUpNow => '立即注册';

  @override
  String get map => '地图';

  @override
  String get mapComingSoon => '地图即将推出';

  @override
  String get mapDescription => '交互式地图视图将在这里可用，用于查看和规划您的旅行路线';

  @override
  String get akihabara => '秋叶原';

  @override
  String get akihabaraAddress => '东京都千代田区外神田';

  @override
  String get jrYamanoteLineAkihabaraStation => 'JR山手线秋叶原站';

  @override
  String get shibuyaCrossing => '涩谷十字路口';

  @override
  String get shibuyaAddress => '东京都涩谷区涩谷';

  @override
  String get walkFromMeijiShrine => '从明治神宫步行15分钟';

  @override
  String get locations => '个地点';

  @override
  String get daySchedule => '天行程';
}
