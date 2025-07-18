import 'package:flutter/material.dart';

class SettingsProvider with ChangeNotifier {
  bool _showUpvotes = true;
  bool _showTimestamp = true;
  int _replyDepthMax = -1; // -1 for infinite

  bool get showUpvotes => _showUpvotes;
  bool get showTimestamp => _showTimestamp;
  int get replyDepthMax => _replyDepthMax;

  void updateShowUpvotes(bool value) {
    _showUpvotes = value;
    notifyListeners();
  }

  void updateShowTimestamp(bool value) {
    _showTimestamp = value;
    notifyListeners();
  }

  void updateReplyDepthMax(int value) {
    _replyDepthMax = value;
    notifyListeners();
  }
}

