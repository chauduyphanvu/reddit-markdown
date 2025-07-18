import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../providers/post_provider.dart';
import 'post_view_screen.dart';
import '../../settings/screens/settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final urlController = TextEditingController();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Reddit Downloader'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Save Reddit Posts as Markdown',
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ).animate().fadeIn(duration: 500.ms),
            const SizedBox(height: 16),
            Text(
              'Enter the URL of a Reddit post below to get started.',
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ).animate().fadeIn(duration: 500.ms, delay: 200.ms),
            const SizedBox(height: 40),
            TextField(
              controller: urlController,
              decoration: const InputDecoration(
                labelText: 'Enter Reddit Post URL',
                border: OutlineInputBorder(),
              ),
            ).animate().fadeIn(duration: 500.ms, delay: 400.ms).slideY(),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                onPressed: () {
                  final url = urlController.text;
                  if (url.isNotEmpty) {
                    context.read<PostProvider>().fetchPost(url);
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const PostViewScreen()),
                    );
                  }
                },
                child: const Text('Fetch Post'),
              ),
            ).animate().fadeIn(duration: 500.ms, delay: 600.ms).slideY(begin: 1),
          ],
        ),
      ),
    );
  }
}

