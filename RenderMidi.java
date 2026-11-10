import com.sun.media.sound.AudioSynthesizer;
import com.sun.media.sound.SoftSynthesizer;
import java.io.File;
import java.util.Map;
import javax.sound.midi.MetaMessage;
import javax.sound.midi.MidiSystem;
import javax.sound.sampled.AudioFileFormat;
import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;

// Render the single-track PPQ MIDI produced by Lua Doom's MUS converter.
class RenderMidi {
    public static void main(String[] args) throws Exception {
        var sequence = MidiSystem.getSequence(new File(args[0]));
        if (sequence.getTracks().length != 1) {
            throw new IllegalArgumentException("Expected a single-track Doom MIDI");
        }
        var format = new AudioFormat(32000, 16, 2, true, false);
        AudioSynthesizer synth = new SoftSynthesizer();
        try (var pcm = synth.openStream(format, Map.of()); var receiver = synth.getReceiver()) {
            var track = sequence.getTracks()[0];
            long previousTick = 0;
            long tempo = 500000;
            long elapsed = 0;
            for (int i = 0; i < track.size(); i++) {
                var event = track.get(i);
                elapsed += (event.getTick() - previousTick) * tempo;
                previousTick = event.getTick();
                if (event.getMessage() instanceof MetaMessage meta) {
                    if (meta.getType() == 0x51) {
                        byte[] data = meta.getData();
                        tempo = (data[0] & 255) << 16 | (data[1] & 255) << 8 | (data[2] & 255);
                    }
                } else {
                    receiver.send(event.getMessage(), elapsed / sequence.getResolution());
                }
            }
            long frames = (elapsed / sequence.getResolution() + 120000) * 32000 / 1000000;
            try (var bounded = new AudioInputStream(pcm, format, frames)) {
                AudioSystem.write(bounded, AudioFileFormat.Type.WAVE, new File(args[1]));
            }
        } finally {
            synth.close();
        }
    }
}
