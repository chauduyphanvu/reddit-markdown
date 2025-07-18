import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/settings_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: Consumer<SettingsProvider>(
        builder: (context, settings, child) {
          return ListView(
            children: [
              SwitchListTile(
                title: const Text('Show Upvotes'),
                value: settings.showUpvotes,
                onChanged: (value) => settings.updateShowUpvotes(value),
              ),
              SwitchListTile(
                title: const Text('Show Timestamps'),
                value: settings.showTimestamp,
                onChanged: (value) => settings.updateShowTimestamp(value),
              ),
              ListTile(
                title: const Text('Max Reply Depth'),
                trailing: DropdownButton<int>(
                  value: settings.replyDepthMax,
                  onChanged: (value) {
                    if (value != null) {
                      settings.updateReplyDepthMax(value);
                    }
                  },
                  items: const [
                    DropdownMenuItem(value: -1, child: Text('Infinite')),
                    DropdownMenuItem(value: 0, child: Text('0')),
                    DropdownMenuItem(value: 1, child: Text('1')),
                    DropdownMenuItem(value: 2, child: Text('2')),
                    DropdownMenuItem(value: 3, child: Text('3')),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

